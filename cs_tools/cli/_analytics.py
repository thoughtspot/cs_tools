"""
Built-in Analytics to CS Tools.

This file localizes all the analytics activities that CS Tools performs.
"""
from __future__ import annotations
from typing import Any, Dict, Optional
import sysconfig
import datetime as dt
import platform
import uuid

from pydantic import validator
from sqlmodel import SQLModel, Field

from cs_tools.sync.sqlite import SQLite
import cs_tools


def get_database(where: str = "local") -> SQLite:
    """Get the local SQLite Analytics database."""
    syncer = SQLite(database_path=cs_tools.const.APP_DIR.resolve().joinpath('analytics.db'), truncate_on_load=False)
    SQLModel.metadata.create_all(bind=syncer.cnxn)
    return syncer


class RuntimeEnvironment(SQLModel, table=True):
    """
    Represent the environment that CS Tools lives in.

    This is an default-anonymous database record of the environment under which CS Tools
    executes commands in.
    """
    __tablename__ = "runtime_environment"

    envt_uuid: str = Field(max_length=32, primary_key=True)
    cs_tools_version: str = Field(default=cs_tools.__version__, primary_key=True)
    capture_dt: dt.datetime = Field(default_factory=dt.datetime.now)
    operating_system: str = Field(default_factory=platform.system)
    python_platform_tag: str = Field(default_factory=sysconfig.get_platform)
    python_version: str = Field(default_factory=platform.python_version)
    envt_company_name: Optional[str] = None

    @validator("envt_company_name", pre=True)
    def _str_lower(cls, value: str) -> str:
        if value is None:
            return value

        return str(value).casefold()

    @validator("envt_uuid", pre=True)
    def _uuid_to_hex_string(cls, value: uuid.UUID) -> str:
        return value.hex


class CommandExecution(SQLModel, table=True):
    """
    Record the execution context.

    This is an default-anonymous database record of the CS Tools command executed.
    """
    __tablename__ = "command_execution"

    envt_uuid: str = Field(max_length=32, primary_key=True)
    start_dt: dt.datetime = Field(primary_key=True)
    end_dt: dt.datetime
    os_args: str
    tool_name: Optional[str] = None
    command_name: Optional[str] = None
    is_success: bool
    is_known_error: Optional[bool] = None
    traceback: Optional[str] = None

    @validator("envt_uuid", pre=True)
    def _uuid_to_hex_string(cls, value: uuid.UUID) -> str:
        return value.hex

    @validator("tool_name")
    def _extract_tool_name(cls, value: str, values: Dict[str, Any]) -> Optional[str]:
        """Here, `value` will always be None."""
        _, _, tools = values["os_args"].partition(" tools ")

        if tools:
            tool_name, *_ = tools.split(" ")
            return tool_name

        return None

    @validator("command_name")
    def _extract_command_name(cls, value: str, values: Dict[str, Any]) -> Optional[str]:
        """Here, `value` will always be None."""
        _, _, tools = values["os_args"].partition(" tools ")

        if len(tools.split(" ")) > 1:
            _, command_name, *_ = tools.split(" ")
            return command_name

        return None
