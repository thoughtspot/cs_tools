"""
Settings describe configurations that are submitted to system like ThoughtSpot.

This is the supply-side of information which determines the runtime environment.
"""

from __future__ import annotations

from typing import Annotated, Any, Optional, Union
import binascii
import datetime as dt
import ipaddress
import json
import logging
import pathlib
import urllib
import urllib.error
import uuid
import zlib

from awesomeversion import AwesomeVersion
import pydantic
import rich
import toml

from cs_tools import __project__, __version__, _compat, _types, errors, utils, validators
from cs_tools.datastructures import ExecutionEnvironment, LocalSystemInfo, _GlobalModel, _GlobalSettings
from cs_tools.updater import cs_tools_venv
from cs_tools.updater._bootstrapper import get_latest_cs_tools_release

_LOG = logging.getLogger(__name__)
_FOUNDING_DAY = dt.datetime(year=2012, month=6, day=1, tzinfo=dt.timezone.utc)


class RemoteRepositoryInfo(_GlobalModel):
    """Information about the most recent CS Tools release."""

    last_checked: Annotated[validators.DateTimeInUTC, validators.as_datetime_isoformat] = _FOUNDING_DAY
    version: Optional[validators.CoerceVersion] = None
    published_at: Optional[Annotated[validators.DateTimeInUTC, validators.as_datetime_isoformat]] = None

    @pydantic.field_validator("last_checked", mode="before")
    @classmethod
    def check_valid_utc_datetime(cls, value: Any) -> dt.datetime:
        if value is None:
            return _FOUNDING_DAY
        return value


class MetaConfig(_GlobalModel):
    """Store information about this environment."""

    install_uuid: uuid.UUID = pydantic.Field(default_factory=uuid.uuid4)
    default_config_name: Optional[str] = None
    remote: RemoteRepositoryInfo = RemoteRepositoryInfo()
    environment: ExecutionEnvironment = ExecutionEnvironment()
    created_in_cs_tools_version: validators.CoerceVersion = __version__
    local_system: LocalSystemInfo = LocalSystemInfo()

    _new_version_notified_ack: bool = False

    @pydantic.model_validator(mode="before")
    @classmethod
    def _enforce_compatability(cls, data: Any) -> Any:
        # DEV NOTE: @boonhapus - upconvert the < 1.4.0 metaconfig
        if data.pop("__is_old_format__", False):
            data = {
                "default_config_name": data.get("default", {}).get("config", None),
                "remote": {
                    "version": data.get("latest_release", {}).get("version", None),
                    "published_at": data.get("latest_release", {}).get("published_at", None),
                },
                "__cs_tools_context__": {"config_migration": {"from": "<1.4.0", "to": __version__}},
            }

        # DEV NOTE: @boonhapus - upconvert the < 1.5.0 metaconfig
        if data and "created_in_cs_tools_version" not in data:
            data = {
                "remote": {
                    "last_checked": data.get("last_remote_check"),
                    "version": data.get("latest_version"),
                    "published_at": data.get("latest_release_date"),
                },
                "analytics": {
                    "is_opted_in": data.get("analytics_opt_in"),
                    "last_checkpoint": data.get("last_analytics_checkpoint"),
                    "can_record_url": bool(data.get("company_name")),
                },
                "__cs_tools_context__": {"config_migration": {"from": "<1.5.0", "to": __version__}},
            }

        # DEV NOTE: @boonhapus - upconvert the < 1.6.0 metaconfig
        if data and "created_in_cs_tools_version" not in data:
            data.pop("analytics", None)

            data = {
                "remote": {
                    "last_checked": data.get("last_remote_check"),
                    "version": data.get("latest_version"),
                    "published_at": data.get("latest_release_date"),
                },
                "__cs_tools_context__": {"config_migration": {"from": "<1.6.0", "to": __version__}},
            }

        return data

    @classmethod
    def load(cls) -> _compat.Self:
        """Read the meta-config."""
        app_dir = cs_tools_venv.base_dir

        OLD_FORMAT = app_dir / ".meta-config.toml"
        NEW_FORMAT = app_dir / ".meta-config.json"

        if OLD_FORMAT.exists():
            data = toml.load(OLD_FORMAT)
            instance = cls(**data, __is_old_format__=True)
            instance = cls(**data)
            OLD_FORMAT.unlink()

        elif NEW_FORMAT.exists():
            data = json.loads(NEW_FORMAT.read_text())
            instance = cls(**data)

        else:
            instance = cls()

        # Can't get the type hints to work here, so will just ignore them for now~
        if "__cs_tools_context__" in instance.__pydantic_extra__:  # type: ignore[operator]
            context = instance.__pydantic_extra__["__cs_tools_context__"]  # type: ignore[index]

            if "config_migration" in context:
                _LOG.info(
                    f"Migrating the meta Configuration file from '{context['config_migration']['from']}' to "
                    f"{context['config_migration']['to']}"
                )
                instance.save()

        instance.check_remote_version()
        return instance

    def save(self) -> None:
        """Store the meta-config."""
        if self.environment.is_ci:
            return

        full_path = cs_tools_venv.base_dir / ".meta-config.json"

        # Don't save extra data.
        self.__pydantic_extra__ = {}

        # Don't save dynamic data.
        data = self.model_dump_json(exclude=["environment"], indent=4)

        full_path.write_text(data)

    def check_remote_version(self) -> None:
        """Check GitHub for the latest cs_tools version."""
        TIMEOUT_AFTER = 0.33
        venv_version = AwesomeVersion(__version__)

        # DONT CHECK REMOTE TOO OFTEN
        # - every 5 hours for BETA
        # - every 1 day   for GENERALLY AVAILABLE
        current_time = dt.datetime.now(tz=dt.timezone.utc)
        remote_delta = dt.timedelta(hours=5) if venv_version.beta else dt.timedelta(days=1)

        if (current_time - self.remote.last_checked) <= remote_delta:
            return

        try:
            data = get_latest_cs_tools_release(timeout=TIMEOUT_AFTER)
            info = {"last_checked": current_time, "version": data["tag_name"], "published_at": data["published_at"]}
            self.remote = RemoteRepositoryInfo.model_validate(info)
            self.save()

        except urllib.error.URLError:
            _LOG.warning(f"Fetching latest CS Tools release version timed out after {TIMEOUT_AFTER}s")

        except FileNotFoundError:
            _LOG.debug("Could not save to .meta-config.json")

        except Exception as e:
            _LOG.debug(f"Could not fetch release url: {e}", exc_info=True)

    def newer_version_string(self) -> str:
        """Return the CLI new version media string."""
        if AwesomeVersion(self.remote.version or "v0.0.0") <= AwesomeVersion(__version__):
            return ""

        from cs_tools.cli.ux import RICH_CONSOLE

        assert self.remote is not None
        assert self.environment is not None

        url = f"{__project__.__repo__}/releases/tag/{self.remote.version}"

        # DEV NOTE: @boonhapus, 2024/03/19
        # It's super likely that we haven't set up logging yet in this part of the process flow.

        if not self._new_version_notified_ack:
            self._new_version_notified_ack = True

            if self.environment.is_ci:
                print(  # noqa: T201
                    f"WARNING: You are using cs tools version {__version__}, however version {self.remote.version} is "
                    f"available. You should consider pinning your dependency to a newer release.\n\nMore information "
                    f"can be found at   {__project__.__repo__}/releases/latest"
                )
            else:
                RICH_CONSOLE.print(
                    rich.panel.Panel.fit(
                        (
                            f"\nOut now, CS Tools version {self.remote.version}!"
                            f"\n\nCheck out the changes in the [b cyan][link={url}]Release Notes[/][/]!"
                            f"\n\nUpgrade with [fg-secondary]cs_tools self update[/]"
                        ),
                        title=":tada: An update has been released! :tada:",
                        title_align="left",
                        border_style="bold green",
                    )
                )

        return ":tada: [fg-success]A new CS Tools version is available![/]"


# GLOBAL SCOPE
_meta_config = MetaConfig.load()


class ThoughtSpotConfiguration(_GlobalSettings):
    url: Union[pydantic.AnyHttpUrl, ipaddress.IPv4Address]
    username: str
    password: Optional[str] = pydantic.Field(default=None)
    secret_key: Optional[_types.GUID] = pydantic.Field(default=None)
    concurrency: Optional[int] = 15
    bearer_token: Optional[str] = pydantic.Field(default=None)
    default_org: Optional[int] = None
    disable_ssl: bool = False
    proxy: Optional[str] = None  # See: https://www.python-httpx.org/advanced/proxies/

    @pydantic.model_validator(mode="before")
    @classmethod
    def ensure_at_least_one_secret(cls, values: Any) -> Any:
        """Must provide one of Password, Secret Key, Bearer Token."""
        if "password" not in values and "secret_key" not in values and "bearer_token" not in values:
            raise ValueError(
                "missing one or more of the following keyword arguments: 'password', 'secret_key', 'bearer_token'"
            )

        return values

    @pydantic.field_validator("password", mode="before")
    @classmethod
    def encode_password(cls, data: Any) -> Optional[str]:
        if data is None:
            return None

        try:
            utils.reveal(data.encode()).decode()
        except (binascii.Error, zlib.error):
            pass
        else:
            return data

        return utils.obscure(data).decode()

    @pydantic.field_validator("url", mode="after")
    @classmethod
    def ensure_only_netloc(cls, data) -> str:
        if isinstance(data, ipaddress.IPv4Address):
            return f"https://{data}"

        netloc = data.host

        if data.scheme == "http" and data.port != 80:
            netloc += f":{data.port}"

        if data.scheme == "https" and data.port != 443:
            netloc += f":{data.port}"

        return f"{data.scheme}://{netloc}"

    @property
    def decoded_password(self) -> str:
        if self.password is None:
            raise ValueError(f"{self.username} has no stored password")
        return utils.reveal(self.password.encode()).decode()

    @property
    def is_orgs_enabled(self) -> bool:
        return self.default_org is not None


class CSToolsConfig(_GlobalSettings):
    """Represents a configuration for CS Tools."""

    name: str
    thoughtspot: ThoughtSpotConfiguration
    verbose: bool = False
    temp_dir: pydantic.DirectoryPath = cs_tools_venv.subdir(".tmp")
    created_in_cs_tools_version: validators.CoerceVersion = __version__

    @pydantic.model_validator(mode="before")
    @classmethod
    def _enforce_compatability(cls, data: Any) -> Any:
        """Perform config file migrations."""
        if data["name"] == "ENV":
            return data

        data = cls._migrate_from_pre_150(data)
        data = cls._migrate_from_pre_160(data)
        return data

    @pydantic.field_serializer("temp_dir")
    @classmethod
    def _serialize_as_string(self, temp_dir: pathlib.Path) -> str:
        if temp_dir is None:
            return None
        return temp_dir.as_posix()

    @classmethod
    def _migrate_from_pre_150(cls, data: Any) -> None:
        """Migrate from historical configs."""
        # ATTR MARKER FOR 1.5.0+
        if "created_in_cs_tools_version" in data:
            return data

        # NEW DATA FORMAT: v1.5.x
        # https://github.com/thoughtspot/cs_tools/blob/21109a43e7e6580b29537978114bbb9a51e5e519/cs_tools/settings.py#L286-L293

        # OLD DATA FORMAT: v1.4.x
        # https://github.com/thoughtspot/cs_tools/blob/0d43bdeb4f84d1d9bbafafb6c93d0074ce24fdf3/cs_tools/settings.py#L201-L207

        # MAJOR CHANGELOG:
        # - remove .syncer
        #   :: this used to describe the default syncer to be used in case no syncer was specified, we removed it in
        #   :: favor of standardizing --syncer as an option name on commands which required it and making a required
        #   :: option instead.
        #
        # - remove .auth in favor of grouping attributes on .thoughtspot
        # - added .created_in_cs_tools_version to help later config migrations
        #
        _IS_REALLY_OLD_FORMAT = data.pop("auth", {})

        data = {
            "name": data["name"],
            "thoughtspot": data.get("thoughtspot", {}) | data.get("auth", {}),
            "verbose": data["verbose"],
            "temp_dir": (
                cs_tools_venv.subdir(".tmp")
                if pathlib.Path(data.get("temp_dir", pathlib.Path())).is_relative_to(cs_tools_venv.base_dir)
                else data["temp_dir"]
            ),
            "created_in_cs_tools_version": __version__,
            "__cs_tools_context__": {"config_migration": {"from": "<1.5.0", "to": __version__}},
        }

        if _IS_REALLY_OLD_FORMAT:
            data["thoughtspot"] = {
                "url": data["thoughtspot"]["host"],
                "username": _IS_REALLY_OLD_FORMAT["frontend"]["username"],
                "password": _IS_REALLY_OLD_FORMAT["frontend"]["password"],
                "disable_ssl": data["thoughtspot"].get("disable_ssl", False),
            }

        return data

    @classmethod
    def _migrate_from_pre_160(cls, data: Any) -> None:
        """Migrate from 1.5.x configs."""
        if AwesomeVersion(data["created_in_cs_tools_version"]) >= AwesomeVersion("1.6.0"):
            return data

        # NEW DATA FORMAT: v1.6.x
        # << THIS FILE >>

        # OLD DATA FORMAT: v1.5.x
        # https://github.com/thoughtspot/cs_tools/blob/0d43bdeb4f84d1d9bbafafb6c93d0074ce24fdf3/cs_tools/settings.py#L201-L207

        # MAJOR CHANGELOG:
        # - unified all the internal directories to be hidden

        data = {
            **data,
            "temp_dir": (
                cs_tools_venv.subdir(".tmp")
                if pathlib.Path(data.get("temp_dir", pathlib.Path())).is_relative_to(cs_tools_venv.base_dir)
                else data["temp_dir"]
            ),
            "created_in_cs_tools_version": __version__,
            "__cs_tools_context__": {
                "config_migration": {
                    "from": data["created_in_cs_tools_version"],
                    "to": __version__,
                },
            },
        }

        return data

    # ====================
    # NORMAL CLASS MEMBERS
    # ====================

    @classmethod
    def exists(cls, name: str) -> bool:
        """Check if a config exists by this name already."""
        return cs_tools_venv.base_dir.joinpath(f"cluster-cfg_{name}.toml").exists()

    @classmethod
    def from_toml(cls, path: pathlib.Path, automigrate: bool = False) -> CSToolsConfig:
        """Read in a cluster-config.toml file."""
        try:
            data = toml.load(path)
        except FileNotFoundError:
            raise errors.ConfigDoesNotExist(config_name=path.stem.replace("cluster-cfg_", "")) from None

        instance = cls.model_validate(data)

        # Can't get the type hints to work here, so will just ignore them for now~
        if "__cs_tools_context__" in instance.__pydantic_extra__:  # type: ignore[operator]
            context = instance.__pydantic_extra__["__cs_tools_context__"]  # type: ignore[index]

            if "config_migration" in context and automigrate:
                _LOG.info(
                    f"Migrating CS Tools configuration file '{instance.name}' from "
                    f"{context['config_migration']['from']} to {context['config_migration']['to']}"
                )
                instance.save()

        return instance

    @classmethod
    def from_name(cls, name: str, automigrate: bool = False, **overrides) -> CSToolsConfig:
        """Read in a config by its name, typically performed on the CLI."""
        if name.upper().startswith("ENV:"):
            name, _, dotfile = name.partition(":")
            return cls.from_environment(name=name, dotfile=dotfile or None)

        conf = cls.from_toml(cs_tools_venv.base_dir / f"cluster-cfg_{name}.toml", automigrate=automigrate)

        if (verbose := overrides.pop("verbose", None)) is not None:
            conf.verbose = verbose

        if (temp_dir := overrides.pop("temp_dir", None)) is not None:
            conf.temp_dir = temp_dir

        if (disable_ssl := overrides.pop("disable_ssl", None)) is not None:
            conf.thoughtspot.disable_ssl = disable_ssl

        return conf

    @classmethod
    def from_environment(cls, name: str = "ENV", *, dotfile: Optional[_types.PathLike] = None) -> CSToolsConfig:
        """Read in a config from environment variables."""
        config = {"name": name}

        if dotfile is not None:
            config["_env_file"] = pathlib.Path(dotfile).as_posix()

        return cls.model_validate(config)

    def save(self, directory: pathlib.Path = cs_tools_venv.base_dir) -> None:
        """Save a cluster-config.toml file."""
        full_path = directory / f"cluster-cfg_{self.name}.toml"

        # Remove the extras, we don't need to save that bit.
        self.__pydantic_extra__ = {}

        with full_path.open(mode="w") as t:
            toml.dump(self.model_dump(), t)
