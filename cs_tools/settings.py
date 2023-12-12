from __future__ import annotations

from ipaddress import IPv4Address
from typing import Annotated, Any, Optional, Union
import binascii
import datetime as dt
import json
import logging
import pathlib
import urllib
import uuid

from awesomeversion import AwesomeVersion
from pydantic import AnyHttpUrl, Field
from pydantic.types import DirectoryPath
import pydantic
import toml

from cs_tools import types, utils, validators
from cs_tools._version import __version__
from cs_tools.datastructures import _GlobalModel, _GlobalSettings
from cs_tools.errors import ConfigDoesNotExist
from cs_tools.updater import cs_tools_venv
from cs_tools.updater._bootstrapper import get_latest_cs_tools_release

log = logging.getLogger(__name__)
_FOUNDING_DAY = dt.datetime(year=2012, month=6, day=1, tzinfo=dt.timezone.utc)


class MetaConfig(_GlobalModel):
    """
    Store information about this environment.
    """

    install_uuid: uuid.UUID = Field(default_factory=uuid.uuid4)
    default_config_name: str = None
    last_remote_check: Annotated[pydantic.AwareDatetime, validators.ensure_datetime_is_utc] = _FOUNDING_DAY
    remote_version: str = None
    remote_date: dt.date = None
    last_analytics_checkpoint: Annotated[pydantic.AwareDatetime, validators.ensure_datetime_is_utc] = _FOUNDING_DAY
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
    default_org: Optional[str] = None
    disable_ssl: bool = False

    @pydantic.field_validator("password", mode="before")
    @classmethod
    def encode_password(cls, data: Any) -> Optional[str]:
        if data is None:
            return None

        try:
            utils.reveal(data.encode()).decode()
        except binascii.Error:
            pass
        else:
            return data

        return utils.obscure(data).decode()

    @pydantic.field_validator("url", mode="after")
    @classmethod
    def ensure_only_netloc(cls, data) -> str:
        netloc = data.host

        if data.scheme == "http" and data.port != 80:
            netloc += str(data.port)

        if data.scheme == "https" and data.port != 443:
            netloc += str(data.port)

        return f"{data.scheme}://{netloc}"

    @property
    def decoded_password(self) -> Optional[str]:
        if self.password is None:
            return None
        return utils.reveal(self.password.encode()).decode()

    @property
    def is_orgs_enabled(self) -> bool:
        return self.default_org is not None


class CSToolsConfig(_GlobalModel):
    name: str
    thoughtspot: ThoughtSpotConfiguration
    verbose: bool = False
    temp_dir: DirectoryPath = cs_tools_venv.app_dir

    @pydantic.model_validator(mode="before")
    @classmethod
    def _enforce_compatability(cls, data: Any) -> Any:
        # from V1.4.x
        if "auth" in data:
            data = cls._backwards_compat_pre_v150(data)

        return data

    @pydantic.field_serializer("temp_dir")
    def ensure_only_netloc(self, temp_dir) -> str:
        return temp_dir.as_posix()

    @classmethod
    def _backwards_compat_pre_v150(cls, data: Any) -> Any:
        """ """
        data = {
            "name": data["name"],
            "thoughtspot": {
                "url": data["thoughtspot"]["host"],
                "username": data["auth"]["frontend"]["username"],
                "password": data["auth"]["frontend"]["password"],
                "disable_ssl": data["thoughtspot"]["disable_ssl"],
            },
            "verbose": data["verbose"],
            "temp_dir": data["temp_dir"],
        }

        return data

    @classmethod
    def from_name(cls, name: str) -> CSToolsConfig:
        """Read in a config by its name."""
        if name is None:
            raise ConfigDoesNotExist(name=f"[b green]{name}")

        return cls.from_toml(cs_tools_venv.app_dir / f"cluster-cfg_{name}.toml")

    @classmethod
    def from_toml(
        cls, fp: pathlib.Path, *, verbose: Optional[bool] = None, temp_dir: Optional[pathlib.Path] = None
    ) -> CSToolsConfig:
        """Read in a ts-config.toml file."""
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

        return cls.model_validate(data, context={"trusted": True})
