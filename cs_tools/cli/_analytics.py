"""
Built-in Analytics to CS Tools.

This file localizes all the analytics activities that CS Tools performs.
"""

from __future__ import annotations

from typing import Annotated, Any, Optional
import datetime as dt
import json
import logging
import os
import platform
import shutil
import sysconfig

from awesomeversion import AwesomeVersion
from rich.align import Align
from rich.panel import Panel
from rich.prompt import Prompt
import httpx
import pydantic
import sqlalchemy as sa
import sqlmodel

from cs_tools import __version__, datastructures, utils, validators
from cs_tools.cli.ux import rich_console
from cs_tools.datastructures import ValidatedSQLModel
from cs_tools.settings import _meta_config as meta
from cs_tools.updater import cs_tools_venv

log = logging.getLogger(__name__)


def get_database() -> sa.engine.Engine:
    """Get the local SQLite Analytics database."""
    if meta.analytics.active_database is not None:
        return meta.analytics.active_database

    db_path = "" if datastructures.ExecutionEnvironment().is_ci else f"/{cs_tools_venv.app_dir / 'analytics.db'}"
    db = sa.create_engine(f"sqlite://{db_path}", future=True)
    meta.analytics.set_database(db)

    with db.begin() as transaction:
        try:
            q = "SELECT cs_tools_version FROM runtime_environment ORDER BY capture_dt DESC LIMIT 1"
            r = transaction.execute(sa.text(q))
            latest_recorded_version = str(r.scalar()) or "0.0.0"

        except sa.exc.OperationalError:
            log.debug("Error fetching data from the database", exc_info=True)
            latest_recorded_version = "0.0.0"

    # PERFROM AN ELEGANT DATABASE MIGRATION :~)
    if __version__ == "1.4.9" and AwesomeVersion(latest_recorded_version) != AwesomeVersion("1.4.9"):
        ValidatedSQLModel.metadata.drop_all(bind=db, tables=[RuntimeEnvironment.__table__, CommandExecution.__table__])

    # SET UP THE DATABASE
    ValidatedSQLModel.metadata.create_all(bind=db, tables=[RuntimeEnvironment.__table__, CommandExecution.__table__])

    # INSERT OUR CURRENT ENVIRONMENT
    if AwesomeVersion(latest_recorded_version) < AwesomeVersion(__version__):
        with db.begin() as transaction:
            envt = RuntimeEnvironment.validated_init(envt_uuid=meta.install_uuid, cs_tools_version=__version__)
            stmt = sa.insert(RuntimeEnvironment).values([envt.model_dump()])
            transaction.execute(stmt)

    return db


def prompt_for_opt_in() -> None:
    """Ask the User if they'd like to send information about their experience."""
    if meta.analytics.is_opted_in is not None:
        return

    if meta.environment.is_ci:
        log.info("Analytics is enabled for CI installs. Set CS_TOOLS_ANALYTICS_OPT_OUT to disable.")
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
    rich_console.print(Align.center(prompt))
    choices = {"yes": True, "no": False, "prompt": None}
    response = Prompt.ask("\n  Response", choices=choices.keys(), console=rich_console)

    if choices[response] is not False and meta.analytics.can_record_url is None:
        choices = {"yes": True, "no": False}
        response = Prompt.ask("\n  Can we record your ThoughtSpot URL?", choices=choices.keys(), console=rich_console)
        meta.analytics.can_record_url = bool(response)

    rich_console.print()
    meta.analytics.is_opted_in = choices[response]
    meta.save()


def maybe_send_analytics_data() -> None:
    """If registered for analytics, regularly send information about the experience."""
    if meta.environment.is_ci and meta.analytics.is_opted_in is None:
        meta.analytics.is_opted_in = "CS_TOOLS_ANALYTICS_OPT_OUT" not in os.environ

    if not meta.analytics.is_opted_in or meta.environment.is_dev:
        return

    db = get_database()

    host = "https://cs-tools-analytics.vercel.app"
    # host = "http://127.0.0.1:8001"

    analytics_checkpoints = []

    with db.begin() as transaction:
        stmt = sa.select(RuntimeEnvironment).where(RuntimeEnvironment.capture_dt >= meta.analytics.last_checkpoint)
        rows = json.dumps([dict(row) for row in transaction.execute(stmt).mappings()], cls=utils.DateTimeEncoder)

        if rows != "[]":
            r_runtimes = httpx.post(f"{host}/analytics/runtimes", data=rows, follow_redirects=True, timeout=None)
            log.debug(f"/analytics/runtimes :: {r_runtimes}")
            analytics_checkpoints.append(r_runtimes.is_success)

        stmt = sa.select(CommandExecution).where(CommandExecution.start_dt >= meta.analytics.last_checkpoint)
        rows = json.dumps([dict(row) for row in transaction.execute(stmt).mappings()], cls=utils.DateTimeEncoder)

        if rows != "[]":
            r_commands = httpx.post(f"{host}/analytics/commands", data=rows, follow_redirects=True, timeout=None)
            log.debug(f"/analytics/commands :: {r_commands}")
            analytics_checkpoints.append(r_commands.is_success)

    if analytics_checkpoints == []:
        log.debug("No analytics checkpoint data to send.")
    elif all(analytics_checkpoints):
        meta.analytics.last_checkpoint = dt.datetime.now(tz=dt.timezone.utc)
        meta.save()
        log.debug("Sent analytics to CS Tools!")
    else:
        log.debug("Failed to send analytics.")


class RuntimeEnvironment(ValidatedSQLModel, table=True):
    """
    Represent the environment that CS Tools lives in.

    This is an default-anonymous database record of the environment under which CS Tools
    executes commands in.
    """

    __tablename__ = "runtime_environment"

    envt_uuid: validators.CoerceHexUUID = sqlmodel.Field(max_length=32, primary_key=True)
    cs_tools_version: validators.CoerceVersion = sqlmodel.Field(primary_key=True)
    capture_dt: validators.DateTimeInUTC = dt.datetime.now(tz=dt.timezone.utc)
    operating_system: str = sqlmodel.Field(default_factory=platform.system)
    is_thoughtspot_cluster: bool = sqlmodel.Field(default_factory=lambda: bool(shutil.which("tscli")))
    python_platform_tag: str = sqlmodel.Field(default_factory=sysconfig.get_platform)
    python_version: validators.CoerceVersion = sqlmodel.Field(default_factory=platform.python_version)


class CommandExecution(ValidatedSQLModel, table=True):
    """
    Record the execution context.

    This is an default-anonymous database record of the CS Tools command executed.
    """

    __tablename__ = "command_execution"

    envt_uuid: validators.CoerceHexUUID = sqlmodel.Field(max_length=32, primary_key=True)
    cs_tools_version: validators.CoerceVersion = sqlmodel.Field(primary_key=True)
    start_dt: validators.DateTimeInUTC = sqlmodel.Field(primary_key=True)
    end_dt: validators.DateTimeInUTC
    is_success: bool
    os_args: str
    tool_name: Optional[str] = None
    command_name: Optional[str] = None
    config_cluster_url: Annotated[Optional[str], validators.ensure_stringified_url_format] = None
    is_known_error: Optional[bool] = None
    traceback: Optional[str] = None

    @pydantic.model_validator(mode="before")
    @classmethod
    def check_input_data_structure(cls, data: Any, info: pydantic.ValidationInfo) -> dict[str, Any]:
        if info.context is utils.State:
            _, _, tool_name_and_args = data["os_args"].partition(" tools ")

            if tool_name_and_args:
                data["tool_name"], *rest = tool_name_and_args.split(" ")

                if rest and not rest[0].startswith("--"):
                    data["command_name"] = rest[1]

            if meta.analytics.can_record_url and (ts := getattr(info.context, "thoughtspot", None)):
                data["config_cluster_url"] = ts.config.thoughtspot.url

        return data
