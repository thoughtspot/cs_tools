from ipaddress import IPv4Address
from typing import Union, Dict, Any
import datetime as dt
import pathlib
import logging
import urllib
import json
import uuid
import re

from pydantic.types import DirectoryPath, FilePath
from awesomeversion import AwesomeVersion
from pydantic import validator, AnyHttpUrl, BaseModel
import toml

from cs_tools.updater._bootstrapper import get_latest_cs_tools_release
from cs_tools._version import __version__
from cs_tools.errors import ConfigDoesNotExist
from cs_tools.const import APP_DIR
from cs_tools import utils

log = logging.getLogger(__name__)


class MetaConfig(BaseModel):
    """
    Store information about this environment.
    """
    install_uuid: uuid.UUID
    default_config_name: str = None
    last_remote_check: dt.datetime = dt.datetime(year=2012, month=6, day=1)
    remote_version: str = None
    remote_date: dt.date = None

    @classmethod
    def load_and_convert_toml(cls):
        """Migrate from the old format."""
        file = APP_DIR.joinpath(".meta-config.toml")
        data = toml.load(file)

        self = cls(
            install_uuid=uuid.uuid4().hex,
            default_config_name=data.get("default", {}).get("config", None),
            # last_remote_check= ... ,
            latest_release_version=data.get("latest_release", {}).get("version", None),
            latest_release_date=data.get("latest_release", {}).get("published_at", None),
        )

        self.save()
        file.unlink()
        return self

    @classmethod
    def load(cls):
        """Read the meta-config."""
        # OLD FORMAT
        if APP_DIR.joinpath(".meta-config.toml").exists():
            self = cls.load_and_convert_toml()

        # NEW FORMAT
        elif APP_DIR.joinpath(".meta-config.json").exists():
            file = APP_DIR.joinpath(".meta-config.json")
            data = json.loads(file.read_text())
            self = cls(**data)

        else:
            self = cls(install_uuid=uuid.uuid4().hex)

        self.check_remote_version()
        return self

    def save(self) -> None:
        """Store the meta-config."""
        file = APP_DIR.joinpath(".meta-config.json")
        data = self.json(indent=4)
        file.write_text(data)

    def check_remote_version(self) -> None:
        """Check GitHub for the latest cs_tools version."""
        venv_version = AwesomeVersion(__version__)
        remote_delta = dt.timedelta(hours=5) if venv_version.beta else dt.timedelta(days=5)
        current_time = dt.datetime.now()

        # don't check too often
        if (current_time - self.last_remote_check) <= remote_delta:
            return

        try:
            data = get_latest_cs_tools_release(allow_beta=venv_version.beta, timeout=0.05)
            self.last_remote_check = current_time
            self.remote_version = data["name"]
            self.remote_date = dt.datetime.strptime(data["published_at"], "%Y-%m-%dT%H:%M:%SZ").date()
            self.save()

        except urllib.error.URLError:
            log.info("fetching latest CS Tools release version timed out")

        except Exception as e:
            log.info(f"could not fetch release url: {e}")

    def newer_version_string(self) -> str:
        """Return the CLI new version media string."""
        if AwesomeVersion(__version__) >= AwesomeVersion(self.remote_version or "v0.0.0"):
            return ""

        url = f"https://github.com/thoughtspot/cs_tools/releases/tag/{self.remote_version}"
        return f"[green]Newer version available![/] [cyan][link={url}]{self.remote_version}[/][/]"


# GLOBAL SCOPE
_meta_config = MetaConfig.load()


class Settings(BaseModel):
    """
    Base class for settings management and validation.
    """

    class Config:
        json_encoders = {FilePath: lambda v: v.resolve().as_posix(), DirectoryPath: lambda v: v.resolve().as_posix()}


class TSCloudURL(str):
    """
    Validator to match against a ThoughtSpot cloud URL.
    """

    REGEX = re.compile(r"(?:https:\/\/)?(.*\.thoughtspot\.cloud)(?:\/.*)?")

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not isinstance(v, str):
            raise TypeError("string required")

        m = cls.REGEX.fullmatch(v)

        if not m:
            raise ValueError("invalid thoughtspot cloud url")

        return cls(f"{m.group(1)}")


class HostConfig(Settings):
    host: Union[AnyHttpUrl, IPv4Address, TSCloudURL]
    port: int = None
    disable_ssl: bool = False
    disable_sso: bool = False

    @property
    def fullpath(self):
        host = self.host
        port = self.port

        if not host.startswith("http"):
            host = f"https://{host}"

        if port:
            port = f":{port}"
        else:
            port = ""

        return f"{host}{port}"

    @validator("host")
    def cast_as_str(v: Any) -> str:
        """
        Converts arguments to a string.
        """
        if hasattr(v, "host"):
            return f"{v.scheme}://{v.host}"

        return str(v)


class AuthConfig(Settings):
    username: str
    password: str = None


class CSToolsConfig(Settings):
    name: str
    thoughtspot: HostConfig
    auth: Dict[str, AuthConfig]
    syncer: Dict[str, FilePath] = None
    verbose: bool = False
    temp_dir: DirectoryPath = APP_DIR

    @validator("syncer")
    def resolve_path(v: Any) -> str:
        if v is None or isinstance(v, dict):
            return v
        return {k: pathlib.Path(f).resolve() for k, f in v.items()}

    @classmethod
    def get_default_config_name(cls) -> str:
        """Return the default config name."""
        return _meta_config.default_config_name

    def dict(self) -> Any:
        """
        Wrapper around model.dict to handle path types.
        """
        data = super().json()
        data = json.loads(data)
        return data

    @classmethod
    def from_toml(cls, fp: pathlib.Path, *, verbose: bool = None, temp_dir: pathlib.Path = None) -> "CSToolsConfig":
        """
        Read in a ts-config.toml file.

        Parameters
        ----------
        fp : pathlib.Path
          location of the config toml on disk

        verbose, temp_dir
          overrides the settings found in the config file
        """
        try:
            data = toml.load(fp)
        except FileNotFoundError:
            raise ConfigDoesNotExist(name=fp.stem.replace("cluster-cfg_", ""))

        if data.get("name") is None:
            data["name"] = fp.stem.replace("cluster-cfg_", "")

        # overrides
        if verbose is not None:
            data["verbose"] = verbose

        if temp_dir is not None:
            data["temp_dir"] = temp_dir

        return cls.parse_obj(data)

    @classmethod
    def from_command(cls, config: str = None, **passthru) -> "CSToolsConfig":
        """
        Read in a ts-config.toml file by its name.

        If no file is provided, we attempt to check for the default
        configuration.

        Parameters
        ----------
        config: str
          name of the configuration file
        """
        if config is None:
            if _meta_config.default_config_name is None:
                raise ConfigDoesNotExist(name="[b green]default[/]")

        return cls.from_toml(APP_DIR / f"cluster-cfg_{_meta_config.default_config_name}.toml", **passthru)

    @classmethod
    def from_parse_args(cls, name: str, *, validate: bool = True, **passthru) -> "CSToolsConfig":
        """
        Validate initial input from config.create or config.modify.
        """
        _pw = passthru.get("password")
        _syncers = [syncer.split("://") for syncer in passthru.get("syncer", [])]

        data = {
            "name": name,
            "verbose": passthru.get("verbose"),
            "temp_dir": passthru.get("temp_dir"),
            "thoughtspot": {
                "host": passthru["host"],
                "port": passthru.get("port"),
                "disable_ssl": passthru.get("disable_ssl"),
                "disable_sso": passthru.get("disable_sso"),
            },
            "auth": {
                "frontend": {
                    "username": passthru["username"],
                    "password": utils.obscure(_pw).decode() if _pw is not None else _pw,
                }
            },
            "syncer": {proto: definition_fp for (proto, definition_fp) in _syncers},
        }

        return cls.parse_obj(data) if validate else cls.construct(**data)
