from typing import List
import itertools as it
import datetime as dt
import logging
import sys

import pendulum
import pydantic
import click
import toml

from cs_tools.errors import CSToolsError, SyncerError
from cs_tools.sync.protocol import SyncerProtocol
from cs_tools.const import PACKAGE_DIR
from cs_tools.sync import register
from cs_tools.data import models


log = logging.getLogger(__name__)


class CommaSeparatedValuesType(click.ParamType):
    """
    Convert arguments to a list of strings.
    """
    name = 'string'

    def convert(
        self,
        value: str,
        param: click.Parameter = None,
        ctx: click.Context = None
    ) -> List[str]:
        if value is None:
            return None

        if not isinstance(value, tuple):
            value = (value, )

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
        validate_only: bool = False
    ) -> SyncerProtocol:
        if value is None:
            return value

        proto, definition = value.split('://')

        if definition in ('default', ''):
            ts_config = ctx.obj.thoughtspot.config

            try:
                definition = ts_config.syncer[proto]
            except (TypeError, KeyError):
                raise SyncerError(
                    proto=proto,
                    cfg=ts_config.name,
                    reason="No default definition has been set for this cluster config.",
                    mitigation=(
                        "Pass the full path to [primary]{proto}://[/] or set a default "
                        "with [primary]cs_tools config modify --config {cfg} --syncer "
                        "{proto}://[blue]path/to/my/default.toml"
                    )
                )

        try:
            cfg = toml.load(definition)
            raise UnicodeDecodeError('1', b'1', 1, 1, '1')
        except (IsADirectoryError, FileNotFoundError):
            raise SyncerError(
                proto=proto,
                definition=definition,
                reason="No {proto} definition found at [blue]{definition}",
                mitigation="You must specify a valid path to a .toml definition file."
            )
        except UnicodeDecodeError:
            raise SyncerError(
                proto=proto,
                definition=definition,
                reason="Couldn't read the Syncer definition at [blue]{definition}[/]",
                mitigation=(
                    "If you're on Windows, you must escape the backslashes in your filepaths, or flip them the other "
                    "way around.\n"
                    "\n  :x: [red]" + r"C:\path\to\my\definition.toml" + "[/]"
                    "\n  :white_heavy_check_mark: [green]" + r"C:\\path\\to\\my\\definition.toml" + "[/]"
                    "\n  :white_heavy_check_mark: [green]" + r"C:/path/to/my/definition.toml" + "[/]"
                )
            )
        except toml.TomlDecodeError:
            raise SyncerError(
                proto=proto,
                definition=definition,
                reason="Your definition file [blue]{definition}[/] is not correct.",
                mitigation=(
                    "Visit the link below to see a full example."
                    "\n[blue]https://thoughtspot.github.io/cs_tools/syncer/{proto}/#full-definition-example"
                )
            )

        if 'manifest' not in cfg:
            cfg['manifest'] = PACKAGE_DIR / 'sync' / proto / 'MANIFEST.json'

        log.info(f'registering syncer: {proto}')
        Syncer = register.load_syncer(protocol=proto, manifest_path=cfg.pop('manifest'))

        try:
            # sanitize input by accepting aliases
            if hasattr(Syncer, '__pydantic_model__'):
                cfg['configuration'] = Syncer.__pydantic_model__.parse_obj(cfg['configuration']).dict()

            syncer = Syncer(**cfg['configuration'])
        except KeyError:
            raise SyncerError(
                proto=proto,
                definition=definition,
                reason="[blue]{definition}[/] is missing a top level marker.",
                mitigation=(
                    "The first line of your definition file should be.."
                    "\n\n[white]\[configuration]"
                )
            )
        except pydantic.ValidationError as e:
            raise SyncerError(
                proto=proto,
                definition=definition,
                errors='\n  '.join([f"[blue]{_['loc'][0]}[/]: {_['msg']}" for _ in e.errors()]),
                reason="[blue]{definition}[/] has incorrect parameters.\n\n  {errors}",
                mitigation=(
                    "Visit the link below to see a full example."
                    "\n[blue]https://thoughtspot.github.io/cs_tools/syncer/{proto}/#full-definition-example"
                )
            )

        # don't actually make lasting changes, just ensure it initializes
        if validate_only:
            return value

        is_database_check = getattr(syncer, '__is_database__', False)
        is_tools_cmd = 'tools' in sys.argv[1:]

        if is_database_check or not is_tools_cmd:
            if getattr(syncer, 'metadata', None) is not None:
                metadata = syncer.metadata
                [t.to_metadata(metadata) for t in models.SQLModel.metadata.sorted_tables]
            else:
                metadata = models.SQLModel.metadata

            metadata.create_all(syncer.cnxn)

            # DEV NOTE: conditionally expose ability to grab views
            if syncer.name != 'falcon':
                metadata.reflect(syncer.cnxn, views=True)

        return syncer
