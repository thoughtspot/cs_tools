from typing import Any, List, Tuple
import collections.abc
import itertools as it
import datetime as dt
import logging

import sqlalchemy
import pendulum
import typer
import click

from cs_tools.cli.dependencies.syncer import DSyncer
from cs_tools._compat import StrEnum

log = logging.getLogger(__name__)


class MultipleChoiceType(click.ParamType):
    name = "TEXT"

    def __init__(self, return_type: type = str, separator: str = ","):
        self.return_type = return_type
        self.separator = separator

    def convert(self, value: str, param: click.Parameter = None, ctx: typer.Context = None) -> List[str]:
        if isinstance(value, str):
            values = [value.split(self.separator)]

        elif isinstance(value, collections.abc.Iterable):
            values = [v.split(",") if isinstance(v, str) else v for v in value]

        return list(self.return_type(v) for v in it.chain.from_iterable(values) if v != "")


class MetadataType(click.ParamType):

    def __init__(self, to_system_types: bool = False, include_subtype: bool = False):
        self.to_system_types = to_system_types
        self.include_subtype = include_subtype
        self.enum = StrEnum(
                        "MetadataType", ["connection", "table", "view", "sql_view", "worksheet", "liveboard", "answer"]
                    )

    def get_metavar(self, param) -> str:
        return "|".join(self.enum)

    def convert(self, value: str, param: click.Parameter = None, ctx: typer.Context = None) -> List[str]:
        if value is None:
            return value

        try:
            value = self.enum(value)
        except ValueError:
            self.fail(f"{value!r} is not a valid {self.__class__.__name__}", param, ctx)

        if self.to_system_types:
            metadata_type, subtype = self.convert_system_types(value)

            if self.include_subtype:
                value = (metadata_type, subtype)
            else:
                value = metadata_type

        return value

    def convert_system_types(self, value) -> Tuple[str, str]:
        mapping = {
            "connection": ("DATA_SOURCE", None),
            "table": ("LOGICAL_TABLE", "ONE_TO_ONE_LOGICAL"),
            "view": ("LOGICAL_TABLE", "AGGR_WORKSHEET"),
            "sql_view": ("LOGICAL_TABLE", "SQL_VIEW"),
            "worksheet": ("LOGICAL_TABLE", "WORKSHEET"),
            "liveboard": ("PINBOARD_ANSWER_BOOK", None),
            "answer": ("QUESTION_ANSWER_BOOK", None),
        }
        return mapping[value]


class CommaSeparatedValuesType(click.ParamType):
    """
    Convert arguments to a list of strings.
    """
    name = "string"

    def __init__(self, *args_passthru, return_type: Any = str, **kwargs_passthru):
        super().__init__(*args_passthru, **kwargs_passthru)
        self.return_type = return_type

    def convert(self, value: str, param: click.Parameter = None, ctx: typer.Context = None) -> List[str]:
        if value is None:
            return None

        if isinstance(value, str):
            values = value.split(",")

        elif isinstance(value, collections.abc.Iterable):
            values = [v.split(",") if isinstance(v, str) else v for v in value]

        return list(self.return_type(v) for v in it.chain.from_iterable(values) if v != "")


class TZAwareDateTimeType(click.ParamType):
    """
    Convert argument to a timezone-aware date.
    """

    name = "datetime"

    def convert(
        self,
        value: dt.datetime,
        param: click.Parameter = None,
        ctx: typer.Context = None,
        locality: str = "local",  # one of: local, utc, server
    ) -> List[str]:
        if value is None:
            return None

        LOCALITY = {"server": ctx.obj.thoughtspot.platform.timezone, "local": pendulum.local_timezone(), "utc": "UTC"}

        tz = LOCALITY[locality]
        return pendulum.instance(value, tz=tz)


class SyncerProtocolType(click.ParamType):
    """
    Convert a path string to a syncer and defintion file.
    """
    name = "path"

    def __init__(self, models: sqlalchemy.Table = None):
        self.models = models

    def get_metavar(self, param) -> str:
        return "protocol://DEFINITION.toml"

    def convert(self, value: str, param: click.Parameter = None, ctx: typer.Context = None) -> DSyncer:
        if value is None:
            return value

        proto, definition = value.split("://")
        syncer_dependency = DSyncer(protocol=proto, definition_fp=definition, parameters=[], models=self.models)
        ctx.command.callback.dependencies.append(syncer_dependency)
        return syncer_dependency
