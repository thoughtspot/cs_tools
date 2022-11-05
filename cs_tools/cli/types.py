from typing import List
import itertools as it
import datetime as dt
import logging

import sqlalchemy
import pendulum
import click

from cs_tools.cli.dependencies.syncer import DSyncer


log = logging.getLogger(__name__)


class CommaSeparatedValuesType(click.ParamType):
    """
    Convert arguments to a list of strings.
    """
    name = 'string'

    def convert(self, value: str, param: click.Parameter = None, ctx: click.Context = None) -> List[str]:
        if value is None:
            return None

        if not isinstance(value, tuple):
            value = (value, )

        if isinstance(value, list):
            return value

        return list(it.chain.from_iterable(v.split(',') for v in value))


class TZAwareDateTimeType(click.ParamType):
    """
    Convert argument to a timezone-aware date.
    """
    name = 'datetime'

    def convert(
        self,
        value: dt.datetime,
        param: click.Parameter = None,
        ctx: click.Context = None,
        locality: str = 'local'  # one of: local, utc, server
    ) -> List[str]:
        if value is None:
            return None

        LOCALITY = {
            'server': ctx.obj.thoughtspot.platform.timezone,
            'local': pendulum.local_timezone(),
            'utc': 'UTC'
        }

        tz = LOCALITY[locality]
        return pendulum.instance(value, tz=tz)


class SyncerProtocolType(click.ParamType):
    """
    Convert a path string to a syncer and defintion file.
    """
    name = 'path'

    def convert(
        self,
        value: str,
        param: click.Parameter = None,
        *,
        ctx: click.Context = None,
        models: sqlalchemy.Table = None
    ) -> DSyncer:
        if value is None:
            return value

        proto, definition = value.split('://')
        syncer_dependency = DSyncer(
            protocol=proto,
            definition_fp=definition,
            parameters=[],
            models=models
        )
        ctx.command.callback.dependencies.append(syncer_dependency)
        return syncer_dependency
