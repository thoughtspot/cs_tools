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
import zoneinfo

from awesomeversion import AwesomeVersion
import pydantic
import pydantic_settings
import sqlalchemy as sa
import sqlmodel

from cs_tools import __project__, __version__, _types, utils, validators

log = logging.getLogger(__name__)
_COMMON_MODEL_CONFIG = {
    "arbitrary_types_allowed": True,
    "extra": "allow",
    "populate_by_name": True,
}


class _GlobalModel(pydantic.BaseModel):
    """Global configuration."""

    model_config = pydantic.ConfigDict(**_COMMON_MODEL_CONFIG)

    @pydantic.model_serializer(mode="wrap")
    def _ignore_extras(self, handler) -> dict[str, Any]:
        return {k: v for k, v in handler(self).items() if k in (self.model_fields | self.model_computed_fields)}

    @pydantic.field_serializer("*", when_used="json")
    @classmethod
    def global_serialization_defaults(cls, v: Any):
        # DATE[TIME]S AS ISO-8601 FORMATTED STRINGS.
        if isinstance(v, (dt.datetime, dt.date)):
            return v.isoformat()
        return v


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
        return cls.model_validate(data, context=context)

    @property
    def clustered_on(self) -> list[sa.Column]:
        """Define the sorting strategy for the given table."""
        return self.__table__.primary_key if self._clustered_on is None else self._clustered_on


class ExecutionEnvironment(_GlobalSettings):
    """Information about the runtime environment."""

    os_args: str = pydantic.Field(default=" ".join(sys.argv))
    is_ci: bool = pydantic.Field(default=False, validation_alias="CI")
    is_dev: bool = pydantic.Field(default_factory=utils.determine_editable_install)

    @pydantic.field_validator("is_ci", mode="plain")
    @classmethod
    def is_ci_pipeline(cls, data: Any) -> bool:
        return bool(data)


class LocalSystemInfo(_GlobalModel):
    """Information about the machine running CS Tools."""

    system: str = f"{platform.system()} (detail: {platform.platform()})"
    python: validators.CoerceVersion = AwesomeVersion(platform.python_version())
    ran_at: Annotated[pydantic.AwareDatetime, validators.ensure_datetime_is_utc] = dt.datetime.now(tz=dt.timezone.utc)

    @pydantic.computed_field
    @property
    def os(self) -> str:
        """The operating system of the machine running CS Tools."""
        friendly_name = {"Windows": "Windows", "Darwin": "MacOS", "Linux": "Linux"}
        os_name, _, _ = self.system.partition(" ")
        return friendly_name[os_name]

    @property
    def is_linux(self) -> bool:
        return self.system.startswith("Linux")

    @property
    def is_mac_osx(self) -> bool:
        return self.system.startswith("Darwin")

    @property
    def is_windows(self) -> bool:
        return self.system.startswith("Windows")


class ThoughtSpotInfo(_GlobalModel):
    """Information about the ThoughtSpot cluster we've established a session with."""

    cluster_id: str
    cluster_name: Optional[str] = "UNKNOWN"
    url: pydantic.AnyUrl
    version: validators.CoerceVersion
    system_users: dict[_types.Name, _types.GUID]
    timezone: zoneinfo.ZoneInfo
    is_cloud: bool
    is_roles_enabled: bool = False
    is_orgs_enabled: bool = False
    is_iam_v2_enabled: bool = False

    @pydantic.model_validator(mode="before")
    @classmethod
    def check_if_from_session_info(cls, data: Any) -> Any:
        if system_info := data.get("__system_info__", {}):
            data["cluster_id"] = system_info["id"]
            data["cluster_name"] = system_info["name"]
            data["url"] = data["__url__"]
            data["version"] = system_info["release_version"]
            data["timezone"] = system_info["time_zone"]
            data["is_cloud"] = system_info["type"] == "SAAS"
            data["is_orgs_enabled"] = data["__is_orgs_enabled__"]
            data["is_roles_enabled"] = data["__is_orgs_enabled__"]
            data["system_users"] = {
                "tsadmin": system_info["tsadmin_user_id"],
                "system": system_info["system_user_id"],
                "su": system_info["super_user_id"],
            }

        if overrides_info := data.get("__overrides_info__", {}).get("config_override_info", {}):
            # data["is_roles_enabled"] = overrides_info.get("orion.rolesEnabled", False)
            # data["is_iam_v2_enabled"] = overrides_info.get("orion.oktaEnabled", False)
            data["is_iam_v2_enabled"] = overrides_info.get("oidcConfiguration.iamV2OIDCEnabled", {}).get(
                "current", False
            )

        return data

    @pydantic.field_validator("version", mode="before")
    @classmethod
    def sanitize_release_version(cls, version_string: str) -> AwesomeVersion:
        major, minor, micro, *rest = version_string.split(".")
        return AwesomeVersion(f"{major}.{minor}.{micro}")

    @pydantic.field_validator("timezone", mode="before")
    @classmethod
    def sanitize_timezone_name(cls, tzname: str) -> zoneinfo.ZoneInfo:
        try:
            tz = zoneinfo.ZoneInfo(key=tzname)
        except zoneinfo.ZoneInfoNotFoundError:
            raise ValueError(f"No timezone found '{tzname}', if this persists try re-installing CS Tools.") from None

        return tz

    @pydantic.field_serializer("url", "timezone")
    @classmethod
    def serialize_as_str(cls, value: Any) -> str:
        return str(value)


class UserInfo(_GlobalModel):
    """Information about the logged in user."""

    guid: _types.GUID
    username: str
    display_name: str
    privileges: set[Union[_types.GroupPrivilege, str]]
    org_context: Optional[int] = None
    email: Optional[pydantic.EmailStr] = None
    auth_context: _types.AuthContext = "NONE"

    @pydantic.model_validator(mode="before")
    @classmethod
    def check_if_from_session_info(cls, data: Any) -> Any:
        if session_info := data.get("__session_info__", {}):
            data = {
                "guid": session_info["id"],
                "username": session_info["name"],
                "display_name": session_info["display_name"],
                "privileges": session_info["privileges"],
                "org_context": (session_info.get("current_org", None) or {}).get("id", None),
                "email": session_info["email"],
                "auth_context": data["__auth_context__"],
            }

        return data

    @pydantic.field_validator("privileges", mode="before")
    @classmethod
    def check_for_new_or_extra_privileges(cls, data):
        for privilege in data:
            try:
                _types.GroupPrivilege(privilege)
            except ValueError:
                log.debug(
                    f"Missing privilege '{privilege}' from CS Tools, please contact us to update it"
                    f"\n{__project__.__help__}"
                )

        return data

    @pydantic.computed_field
    @property
    def is_admin(self) -> bool:
        """Whether or not we're an Admin."""
        allowed = {_types.GroupPrivilege.can_administer_thoughtspot}
        return bool(allowed.intersection(self.privileges))

    @pydantic.computed_field
    @property
    def is_data_manager(self) -> bool:
        """Whether or not we're able to create objects under the Data tab."""
        allowed = {_types.GroupPrivilege.can_administer_thoughtspot, _types.GroupPrivilege.can_manage_data}
        return bool(allowed.intersection(self.privileges))


class SessionContext(_GlobalModel):
    """Information about the current CS Tools session."""

    cs_tools_version: validators.CoerceVersion = AwesomeVersion(__version__)
    environment: ExecutionEnvironment = ExecutionEnvironment()
    thoughtspot: ThoughtSpotInfo
    system: LocalSystemInfo = LocalSystemInfo()
    user: UserInfo
