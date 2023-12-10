from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional, Union
import datetime as dt
import json
import logging
import urllib
import uuid

from awesomeversion import AwesomeVersion
from pydantic import AnyHttpUrl, Field
import pydantic
import toml

from cs_tools import types, utils
from cs_tools._version import __version__
from cs_tools.datastructures import _GlobalModel, _GlobalSettings
from cs_tools.errors import ConfigDoesNotExist
from cs_tools.updater import cs_tools_venv
from cs_tools.updater._bootstrapper import get_latest_cs_tools_release

if TYPE_CHECKING:
    from ipaddress import IPv4Address
    import pathlib

    from pydantic.types import DirectoryPath, FilePath

log = logging.getLogger(__name__)


class MetaConfig(_GlobalModel):
    """
    Store information about this environment.
    """

    install_uuid: uuid.UUID = Field(default_factory=uuid.uuid4)
    default_config_name: str = None
    last_remote_check: dt.datetime = dt.datetime(year=2012, month=6, day=1, tzinfo=dt.timezone.utc)
    remote_version: str = None
    remote_date: dt.date = None
    last_analytics_checkpoint: dt.datetime = dt.datetime(year=2012, month=6, day=1, tzinfo=dt.timezone.utc)
    analytics_opt_in: Optional[bool] = None
    # company_name: Optional[str] = None  # DEPRECATED AS OF 1.4.6
    record_thoughtspot_url: Optional[bool] = None

    @classmethod
    def load_and_convert_toml(cls):
        """Migrate from the old format."""
        data = toml.load(cs_tools_venv.app_dir.joinpath(".meta-config.toml"))

        self = cls(
            # install_uuid=...,
            default_config_name=data.get("default", {}).get("config", None),
            # last_remote_check= ... ,
            latest_release_version=data.get("latest_release", {}).get("version", None),
            latest_release_date=data.get("latest_release", {}).get("published_at", None),
            # last_analytics_checkpoint= ...,
        )

        return self

    @classmethod
    def load(cls):
        """Read the meta-config."""
        app_dir = cs_tools_venv.app_dir

        # OLD FORMAT
        if app_dir.joinpath(".meta-config.toml").exists():
            self = cls.load_and_convert_toml()
            self.save()

            # REMOVE OLD DATA
            app_dir.joinpath(".meta-config.toml").unlink()

        # NEW FORMAT
        elif app_dir.joinpath(".meta-config.json").exists():
            file = app_dir.joinpath(".meta-config.json")
            data = json.loads(file.read_text())

            if data.get("company_name", None) is not None:
                data["record_thoughtspot_url"] = True

            self = cls(**data)

        # NEVER SEEN BEFORE
        else:
            self = cls()

        self.check_remote_version()
        return self

    def save(self) -> None:
        """Store the meta-config."""
        file = cs_tools_venv.app_dir.joinpath(".meta-config.json")
        data = self.json(indent=4)
        file.write_text(data)

    def check_remote_version(self) -> None:
        """Check GitHub for the latest cs_tools version."""
        venv_version = AwesomeVersion(__version__)
        remote_delta = dt.timedelta(hours=5) if venv_version.beta else dt.timedelta(days=1)
        current_time = dt.datetime.now(tz=dt.timezone.utc)

        # don't check too often
        if (current_time - self.last_remote_check) <= remote_delta:
            return

        try:
            data = get_latest_cs_tools_release(allow_beta=venv_version.beta, timeout=0.33)
            self.last_remote_check = current_time
            self.remote_version = data["name"]
            self.remote_date = (
                dt.datetime.strptime(data["published_at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=dt.timezone.utc).date()
            )
            self.save()

        except urllib.error.URLError:
            log.info("fetching latest CS Tools release version timed out")

        except Exception as e:
            log.info(f"could not fetch release url: {e}")

    def newer_version_string(self) -> str:
        """Return the CLI new version media string."""
        if AwesomeVersion(self.remote_version or "v0.0.0") <= AwesomeVersion(__version__):
            return ""

        url = f"https://github.com/thoughtspot/cs_tools/releases/tag/{self.remote_version}"
        msg = f"[green]Newer version available![/] [cyan][link={url}]{self.remote_version}[/][/]"
        log.info(msg)
        return msg


# GLOBAL SCOPE
_meta_config = MetaConfig.load()


class ThoughtSpotConfiguration(_GlobalSettings):
    url: Union[AnyHttpUrl, IPv4Address]
    username: str
    password: Optional[str] = pydantic.Field(default=None)
    secret_key: Optional[types.GUID] = pydantic.Field(default=None)
    org_id: Optional[int] = None
    disable_ssl: bool = False

    @property
    def decoded_password(self) -> str:
        return utils.reveal(self.password).decode()

    @property
    def is_orgs_enabled(self) -> bool:
        return self.org_id is not None


class CSToolsConfig(_GlobalModel):
    name: str
    thoughtspot: ThoughtSpotConfiguration
    syncer: dict[str, FilePath] = None
    verbose: bool = False
    temp_dir: DirectoryPath = cs_tools_venv.app_dir

    @pydantic.model_validator(mode="before")
    @classmethod
    def _check_backwards_compatability(cls, data: Any) -> Any:
        # from V1.4.x
        if "auth" in data:
            data = {
                "name": data["name"],
                "thoughtspot": {
                    "url": data["thoughtspot"]["host"],
                    "username": data["auth"]["frontend"]["username"],
                    "password": data["auth"]["frontend"]["password"],
                    "disable_ssl": data["thoughtspot"]["disable_ssl"],
                },
                "syncer": data.get("syncer", {}),
                "verbose": data["verbose"],
                "temp_dir": data["temp_dir"],
            }

        return data

    @classmethod
    def from_toml(
        cls, fp: pathlib.Path, *, verbose: Optional[bool] = None, temp_dir: Optional[pathlib.Path] = None
    ) -> CSToolsConfig:
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
            raise ConfigDoesNotExist(name=fp.stem.replace("cluster-cfg_", "")) from None

        if data.get("name") is None:
            data["name"] = fp.stem.replace("cluster-cfg_", "")

        # overrides
        if verbose is not None:
            data["verbose"] = verbose

        if temp_dir is not None:
            data["temp_dir"] = temp_dir

        return cls(**data)

    @classmethod
    def from_command(cls, config: Optional[str] = None, **passthru) -> CSToolsConfig:
        """
        Read in a ts-config.toml file by its name.

        If no file is provided, we attempt to check for the default
        configuration.

        Parameters
        ----------
        config: str
          name of the configuration file
        """
        if config is None and _meta_config.default_config_name is not None:
            config = _meta_config.default_config_name

        if config is None:
            raise ConfigDoesNotExist(name=f"[b green]{config}")

        return cls.from_toml(cs_tools_venv.app_dir / f"cluster-cfg_{config}.toml", **passthru)

    @classmethod
    def from_parse_args(cls, name: str, *, validate: bool = True, **passthru) -> CSToolsConfig:
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
            "syncer": dict(_syncers),
        }

        return cls.model_validate(data) if validate else cls.construct(**data)
