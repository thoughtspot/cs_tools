"""
Datastructures describe objects which describe systems at runtime for a given session.

This is the receiving side of the configuration for a session. (settings.py)

This includes things that will change based on submitted user configuration.
- ThoughtSpot
- Local Machine
- User
"""
from __future__ import annotations

from typing import Annotated, Any, Optional
import datetime as dt
import platform
import sys

from awesomeversion import AwesomeVersion
import pydantic
import pydantic_settings
import sqlmodel

from cs_tools import types, utils, validators
from cs_tools._version import __version__

_COMMON_MODEL_CONFIG = {
    "arbitrary_types_allowed": True,
    "extra": "allow",
    "populate_by_name": True,
}


class _GlobalModel(pydantic.BaseModel):
    """Global configuration."""

    model_config = pydantic.ConfigDict(**_COMMON_MODEL_CONFIG)


class _GlobalSettings(pydantic_settings.BaseSettings):
    """
    Global configuration.

    Can inherit model attributes from environment variables.
    """

    model_config = pydantic_settings.SettingsConfigDict(env_prefix="CS_TOOLS_", **_COMMON_MODEL_CONFIG)


class ValidatedSQLModel(sqlmodel.SQLModel):
    """
    Global SQLModel configuration.

    Can inherit model attributes from environment variables.
    """

    model_config = sqlmodel._compat.SQLModelConfig(env_prefix="CS_TOOLS_SYNCER_", **_COMMON_MODEL_CONFIG)

    @classmethod
    def validated_init(cls, context: Any = None, **data):
        # defaults  = cls.read_from_environment()
        # sanitized = cls.model_validate({**defaults, **data})
        sanitized = cls.model_validate(data, context=context)
        return cls(**sanitized.model_dump())


class ExecutionEnvironment(_GlobalSettings):
    """Information about the runtime environment."""

    os_args: str = pydantic.Field(default=" ".join(sys.argv))
    is_ci: bool = pydantic.Field(default="DEFINITELY_NOT_CI", validation_alias="CI")
    is_dev: bool = pydantic.Field(default_factory=utils.determine_editable_install)

    @pydantic.field_validator("is_ci", mode="plain")
    @classmethod
    def is_ci_pipeline(cls, data: Any) -> bool:
        return data != "DEFINITELY_NOT_CI"


class ThoughtSpotInfo(_GlobalModel):
    """Information about the ThoughtSpot cluster we've established a session with."""

    cluster_id: str
    url: pydantic.AnyUrl
    version: validators.CoerceVersion
    timezone: str
    is_cloud: bool
    is_api_v2_enabled: bool = False
    is_roles_enabled: bool = False
    is_orgs_enabled: bool = False

    @pydantic.model_validator(mode="before")
    @classmethod
    def check_if_from_session_info(cls, data: Any) -> Any:
        if "__is_session_info__" in data:
            config_info = data.get("configInfo")

            data = {
                "cluster_id": config_info["selfClusterId"],
                "url": data["__url__"],
                "version": data["releaseVersion"],
                "timezone": data["timezone"],
                "is_cloud": config_info.get("isSaas", False),
            }

        return data

    @pydantic.field_validator("version", mode="before")
    @classmethod
    def sanitize_release_version(cls, version_string: str) -> AwesomeVersion:
        major, minor, micro, *rest = version_string.split(".")
        return AwesomeVersion(f"{major}.{minor}.{micro}")


class LocalSystemInfo(_GlobalModel):
    """Information about the machine running CS Tools."""

    system: str = f"{platform.system()} (detail: {platform.platform()})"
    python: validators.CoerceVersion = AwesomeVersion(platform.python_version())
    ran_at: Annotated[pydantic.AwareDatetime, validators.ensure_datetime_is_utc] = dt.datetime.now(tz=dt.timezone.utc)


class UserInfo(_GlobalModel):
    """Information about the logged in user."""

    guid: pydantic.UUID4
    username: str
    display_name: str
    privileges: set[types.GroupPrivilege]
    email: Optional[pydantic.EmailStr] = None

    @pydantic.model_validator(mode="before")
    @classmethod
    def check_if_from_session_info(cls, data: Any) -> Any:
        if "__is_session_info__" in data:
            data = {
                "guid": data["userGUID"],
                "username": data["userName"],
                "display_name": data["userDisplayName"],
                "privileges": data["privileges"],
                "email": data.get("userEmail", None),
            }

        return data

    @property
    def is_admin(self) -> bool:
        allowed = {types.GroupPrivilege.can_administer_thoughtspot}
        return bool(allowed.intersection(self.privileges))

    @property
    def is_data_manager(self) -> bool:
        allowed = {types.GroupPrivilege.can_administer_thoughtspot, types.GroupPrivilege.can_manage_data}
        return bool(allowed.intersection(self.privileges))


class SessionContext(_GlobalModel):
    """Information about the current CS Tools session."""

    cs_tools_version: validators.CoerceVersion = AwesomeVersion(__version__)
    environment: Optional[ExecutionEnvironment]
    thoughtspot: ThoughtSpotInfo
    system: Optional[LocalSystemInfo]
    user: UserInfo
