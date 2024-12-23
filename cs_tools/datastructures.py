"""
Datastructures describe objects which describe systems at runtime for a given session.

This is the receiving side of the configuration for a session. (settings.py)

This includes things that will change based on submitted user configuration.
- ThoughtSpot
- Local Machine
- User
"""

from __future__ import annotations

from typing import Annotated, Any, Literal
import datetime as dt
import logging
import platform
import sys

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

    _clustered_on: list[sa.Column] | None = pydantic.PrivateAttr(None)

    @pydantic.model_serializer(mode="wrap")
    def _ignore_extras(self, handler) -> dict[str, Any]:
        return {k: v for k, v in handler(self).items() if k in self.model_fields}

    @classmethod
    def validated_init(cls, context: Any = None, **data):
        # defaults  = cls.read_from_environment()
        return cls.model_validate(data, context=context)

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
    is_roles_enabled: bool = False
    is_orgs_enabled: bool = False

    @pydantic.model_validator(mode="before")
    @classmethod
    def check_if_from_session_info(cls, data: Any) -> Any:
        if "__system_info__" in data:
            data = {
                "url": data["__url__"],
                "is_orgs_enabled": data["__is_orgs_enabled__"],
                "is_roles_enabled": data["__system_info__"].get("roles_enabled", False),
                "cluster_id": data["__system_info__"]["id"],
                "version": data["__system_info__"]["release_version"],
                "timezone": data["__system_info__"]["time_zone"],
                "is_cloud": data["__system_info__"]["type"] == "SAAS",
            }

        return data

    @pydantic.field_validator("version", mode="before")
    @classmethod
    def sanitize_release_version(cls, version_string: str) -> AwesomeVersion:
        major, minor, micro, *rest = version_string.split(".")
        return AwesomeVersion(f"{major}.{minor}.{micro}")

    @pydantic.field_serializer("url")
    @classmethod
    def serialize_as_str(cls, url: pydantic.AnyUrl) -> str:
        return str(url)


class LocalSystemInfo(_GlobalModel):
    """Information about the machine running CS Tools."""

    system: str = f"{platform.system()} (detail: {platform.platform()})"
    python: validators.CoerceVersion = AwesomeVersion(platform.python_version())
    ran_at: Annotated[pydantic.AwareDatetime, validators.ensure_datetime_is_utc] = dt.datetime.now(tz=dt.timezone.utc)

    @property
    def is_linux(self) -> bool:
        return self.system.startswith("Linux")

    @property
    def is_mac_osx(self) -> bool:
        return self.system.startswith("Darwin")

    @property
    def is_windows(self) -> bool:
        return self.system.startswith("Windows")


class UserInfo(_GlobalModel):
    """Information about the logged in user."""

    guid: types.GUID
    username: str
    display_name: str
    privileges: set[types.GroupPrivilege | str]
    org_context: int | None = None
    email: pydantic.EmailStr | None = None

    @pydantic.model_validator(mode="before")
    @classmethod
    def check_if_from_session_info(cls, data: Any) -> Any:
        if "__session_info__" in data:
            data = {
                "guid": data["__session_info__"]["id"],
                "username": data["__session_info__"]["name"],
                "display_name": data["__session_info__"]["display_name"],
                "privileges": data["__session_info__"]["privileges"],
                "org_context": (data["__session_info__"].get("current_org", None) or {}).get("id", None),
                "email": data["__session_info__"]["email"],
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
    environment: ExecutionEnvironment = ExecutionEnvironment()
    thoughtspot: ThoughtSpotInfo
    system: LocalSystemInfo = LocalSystemInfo()
    user: UserInfo
