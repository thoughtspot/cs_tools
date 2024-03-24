"""
Datastructures describe objects which describe systems at runtime for a given session.

This is the receiving side of the configuration for a session. (settings.py)

This includes things that will change based on submitted user configuration.
- ThoughtSpot
- Local Machine
- User
"""
from __future__ import annotations

from typing import Annotated, Any, Optional, Union
import datetime as dt
import logging
import platform
import sys
import uuid

from awesomeversion import AwesomeVersion
import pydantic
import pydantic_settings
import sqlalchemy as sa
import sqlmodel

from cs_tools import __project__, __version__, types, utils, validators

log = logging.getLogger(__name__)
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

    model_config = pydantic_settings.SettingsConfigDict(
        env_prefix="CS_TOOLS_", env_nested_delimiter="__", **_COMMON_MODEL_CONFIG
    )


class ValidatedSQLModel(sqlmodel.SQLModel):
    """
    Global SQLModel configuration.

    Can inherit model attributes from environment variables.
    """

    model_config = sqlmodel._compat.SQLModelConfig(env_prefix="CS_TOOLS_SYNCER_", **_COMMON_MODEL_CONFIG)

    _clustered_on: Optional[list[sa.Column]] = pydantic.PrivateAttr(None)

    @pydantic.model_serializer(mode="wrap")
    def _ignore_extras(self, handler) -> dict[str, Any]:
        return {k: v for k, v in handler(self).items() if k in self.model_fields}

    @classmethod
    def validated_init(cls, context: Any = None, **data):
        # defaults  = cls.read_from_environment()
        # sanitized = cls.model_validate({**defaults, **data})
        sanitized = cls.model_validate(data, context=context)
        return cls(**sanitized.model_dump())

    @property
    def clustered_on(self) -> list[sa.Column]:
        """Define the sorting strategy for the given table."""
        return self.__table__.primary_key if self._clustered_on is None else self._clustered_on


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
    notification_banner: Optional[types.ThoughtSpotNotificationBanner] = None

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
                # DEV NOTE: @boonhapus, 2024/01/31
                #   maybe we pick a ThoughtSpot version where V2 APIs are stable enough to switch to for the majority of
                #   workflows instead?
                "is_api_v2_enabled": config_info.get("tseRestApiV2PlaygroundEnabled", False),
                "is_roles_enabled": config_info.get("rolesEnabled", False),
                "is_orgs_enabled": data["__is_orgs_enabled__"],
                "notification_banner": data.get("notificationBanner", None),
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

    guid: uuid.UUID
    username: str
    display_name: str
    privileges: set[Union[types.GroupPrivilege, str]]
    org_context: Optional[int]
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
                "org_context": data.get("currentOrgId", None),
                "email": data.get("userEmail", None),
            }

        return data

    @pydantic.field_validator("privileges", mode="before")
    @classmethod
    def check_for_new_or_extra_privileges(cls, data):
        for privilege in data:
            try:
                types.GroupPrivilege(privilege)
            except ValueError:
                log.debug(
                    f"Missing privilege '{privilege}' from CS Tools, please contact us to update it"
                    f"\n{__project__.__help__}"
                )

        return data

    @property
    def is_admin(self) -> bool:
        """Whether or not we're an Admin."""
        allowed = {types.GroupPrivilege.can_administer_thoughtspot}
        return bool(allowed.intersection(self.privileges))

    @property
    def is_data_manager(self) -> bool:
        """Whether or not we're able to create objects under the Data tab."""
        allowed = {types.GroupPrivilege.can_administer_thoughtspot, types.GroupPrivilege.can_manage_data}
        return bool(allowed.intersection(self.privileges))


class SessionContext(_GlobalModel):
    """Information about the current CS Tools session."""

    cs_tools_version: validators.CoerceVersion = AwesomeVersion(__version__)
    environment: Optional[ExecutionEnvironment]
    thoughtspot: ThoughtSpotInfo
    system: Optional[LocalSystemInfo]
    user: UserInfo
