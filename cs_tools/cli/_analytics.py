"""
Built-in Analytics to CS Tools.

This file localizes all the analytics activities that CS Tools performs.
"""
from __future__ import annotations
from typing import Any, Dict, Optional, Union
import sysconfig
import datetime as dt
import platform
import logging
import shutil
import uuid
import json

from awesomeversion import AwesomeVersion
from rich.prompt import Prompt
from pydantic import validator
from sqlmodel import SQLModel, Field
import sqlalchemy as sa
import httpx
from rich.panel import Panel

from cs_tools.updater import cs_tools_venv
from cs_tools._version import __version__
from cs_tools.settings import _meta_config as meta
from cs_tools.cli.ux import rich_console
from cs_tools import utils

log = logging.getLogger(__name__)


def get_database() -> sa.engine.Engine:
    """Get the local SQLite Analytics database."""
    db_path = cs_tools_venv.app_dir.resolve().joinpath("analytics.db")
    db = sa.create_engine(f"sqlite:///{db_path}", future=True)

    with db.begin() as transaction:
        try:
            r = transaction.execute(sa.text("""SELECT MAX(cs_tools_version) FROM runtime_environment"""))
            latest_recorded_version = r.scalar() or "0.0.0"

        except sa.exc.OperationalError:
            log.debug("Error fetching data from the database", exc_info=True)
            latest_recorded_version = "0.0.0"

        # PERFROM AN ELEGANT DATABASE MIGRATION :~)
        if AwesomeVersion(latest_recorded_version) < AwesomeVersion("1.4.7"):
            SQLModel.metadata.drop_all(bind=db)
    
    SQLModel.metadata.create_all(bind=db, tables=[RuntimeEnvironment.__table__, CommandExecution.__table__])

    # SET UP THE DATABASE
    if AwesomeVersion(latest_recorded_version) < AwesomeVersion("1.4.7"):
        data = {"envt_uuid": meta.install_uuid, "cs_tools_version": __version__}

        with db.begin() as transaction:
            stmt = sa.insert(RuntimeEnvironment).values([RuntimeEnvironment(**data).dict()])
            transaction.execute(stmt)

    return db


def prompt_for_opt_in() -> None:
    """ """
    if meta.analytics_opt_in is not None:
        return

    rich_console.print()

    prompt = Panel.fit(
        (
            "We use this information to help the ThoughtSpot Product team prioritize new features."
            "\n"
            "\n- CS Tools Environment UUID \t - CS Tools Version"
            "[dim]\n- Today's Date \t\t\t - Your Operating System (Windows, Mac, Linux)[/]"
            "\n- Python Platform Tag \t\t - Python Version"
            "[dim]\n- Whether or not you run CS Tools on the ThoughtSpot cluster[/]"
        ),
        title="[b blue]Would you like to send analytics to the CS Tools team?",
        border_style="bold blue",
    )
    rich_console.print(prompt)
    choices = {"yes": True, "no": False, "prompt": None}
    response = Prompt.ask("\n  Response", choices=choices.keys(), console=rich_console)

    if choices[response] is not False and meta.record_thoughtspot_url is None:
        choices = {"yes": True, "no": False}
        response = Prompt.ask("\n  Can we record your ThoughtSpot URL?", choices=choices.keys(), console=rich_console)
        meta.record_thoughtspot_url = bool(response)

    rich_console.print()
    meta.analytics_opt_in = choices[response]
    meta.save()


def maybe_send_analytics_data() -> None:
    """ """
    db = get_database()

    if meta.analytics_opt_in is None:
        prompt_for_opt_in()

    if meta.analytics_opt_in is False:
        return

    host = "https://cs-tools-analytics.vercel.app"
    # host = "http://127.0.0.1:8001"

    analytics_checkpoints = []

    with db.begin() as transaction:
        stmt = sa.select(RuntimeEnvironment).where(RuntimeEnvironment.capture_dt >= meta.last_analytics_checkpoint)
        rows = json.dumps([dict(row) for row in transaction.execute(stmt).mappings()], cls=utils.DateTimeEncoder)

        if rows != "[]":
            r_runtimes = httpx.post(f"{host}/analytics/runtimes", data=rows, follow_redirects=True, timeout=None)
            log.debug(r_runtimes.text)
            analytics_checkpoints.append(r_runtimes.is_success)

        stmt = sa.select(CommandExecution).where(CommandExecution.start_dt >= meta.last_analytics_checkpoint)
        rows = json.dumps([dict(row) for row in transaction.execute(stmt).mappings()], cls=utils.DateTimeEncoder)

        if rows != "[]":
            r_commands = httpx.post(f"{host}/analytics/commands", data=rows, follow_redirects=True, timeout=None)
            log.debug(r_commands.text)
            analytics_checkpoints.append(r_commands.is_success)

    if analytics_checkpoints == []:
        log.debug("No analytics checkpoint data to send.")
    elif all(analytics_checkpoints):
        meta.last_analytics_checkpoint = dt.datetime.utcnow()
        meta.save()
        log.debug("Sent analytics to CS Tools!")
    else:
        log.debug("Failed to send analytics.")


class RuntimeEnvironment(SQLModel, table=True):
    """
    Represent the environment that CS Tools lives in.

    This is an default-anonymous database record of the environment under which CS Tools
    executes commands in.
    """
    __tablename__ = "runtime_environment"

    envt_uuid: str = Field(max_length=32, primary_key=True)
    cs_tools_version: str = Field(primary_key=True)
    capture_dt: dt.datetime = Field(default_factory=dt.datetime.utcnow)
    operating_system: str = Field(default_factory=platform.system)
    is_thoughtspot_cluster: str = Field(default_factory=lambda: bool(shutil.which("tscli")))
    python_platform_tag: str = Field(default_factory=sysconfig.get_platform)
    python_version: str = Field(default_factory=platform.python_version)

    @validator("envt_uuid", pre=True)
    def _uuid_to_hex_string(cls, value: Union[uuid.UUID, str]) -> str:
        if isinstance(value, uuid.UUID):
            return value.hex
        return value


class CommandExecution(SQLModel, table=True):
    """
    Record the execution context.

    This is an default-anonymous database record of the CS Tools command executed.
    """
    __tablename__ = "command_execution"

    envt_uuid: str = Field(max_length=32, primary_key=True)
    cs_tools_version: str = Field(primary_key=True)
    start_dt: dt.datetime = Field(primary_key=True)
    end_dt: dt.datetime
    is_success: bool
    os_args: str
    tool_name: Optional[str] = None
    command_name: Optional[str] = None
    config_cluster_url: Optional[str] = None
    is_known_error: Optional[bool] = None
    traceback: Optional[str] = None

    @validator("envt_uuid", pre=True)
    def _uuid_to_hex_string(cls, value: Union[uuid.UUID, str]) -> str:
        if isinstance(value, uuid.UUID):
            return value.hex
        return value

    @validator("tool_name", always=True)
    def _extract_tool_name(cls, value: Any, values: Dict[str, Any]) -> Optional[str]:
        """Here, `value` will always be None."""
        _, _, tools = values["os_args"].partition(" tools ")

        if tools:
            tool_name, *_ = tools.split(" ")
            return tool_name

        return None

    @validator("command_name", always=True)
    def _extract_command_name(cls, value: Any, values: Dict[str, Any]) -> Optional[str]:
        """Here, `value` will always be None."""
        _, _, tools = values["os_args"].partition(" tools ")

        if len(tools.split(" ")) > 1:
            _, command_name, *_ = tools.split(" ")
            return command_name

        return None

    @validator("config_cluster_url", pre=True)
    def _extract_config_cluster_url(cls, value: Any) -> Optional[str]:
        if isinstance(value, utils.State) and hasattr(value, "thoughtspot"):
            return value.thoughtspot.platform.url

        if isinstance(value, str):
            return value

        return None
