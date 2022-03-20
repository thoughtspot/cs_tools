from inspect import Signature, Parameter
from typing import Any, Callable, Dict, List, Optional, Tuple
import itertools as it
import logging
import pathlib
import re

from pydantic.dataclasses import dataclass
from click.exceptions import UsageError
from rich.console import Console
from typer.models import ParamMeta
from rich.table import Table
from typer.main import get_click_param
from pydantic import validator
from typer import Argument as A_, Option as O_
import typer
import click
import toml

from cs_tools.helpers.loader import CSTool
from cs_tools.sync.protocol import SyncerProtocol
from cs_tools.thoughtspot import ThoughtSpot
from cs_tools.settings import TSConfig
from cs_tools.const import CONSOLE_THEME, PACKAGE_DIR
from cs_tools.data import models
from cs_tools.sync import register
from cs_tools import __version__, util


log = logging.getLogger(__name__)


class SyncerProtocolType(click.ParamType):
    """
    Convert a path string to a syncer and defintion file.
    """
    name = 'path'

    def convert(
        self,
        value: str,
        param: click.Parameter = None,
        ctx: click.Context = None
    ) -> SyncerProtocol:
        proto, definition = value.split('://')
        cfg = toml.load(definition)

        if proto != 'custom':
            cfg['manifest'] = pathlib.Path(__file__).parent.parent / 'sync' / proto / 'MANIFEST.json'

        Syncer = register.load_syncer(protocol=proto, manifest_path=cfg.pop('manifest'))
        syncer = Syncer(**cfg['configuration'])
        log.info(f'registering syncer: {syncer.name}')

        if getattr(syncer, '__is_database__', False):
            models.SQLModel.metadata.create_all(syncer.engine)

        return syncer


@dataclass
class Dependency:
    name: str
    to_call: Callable
    option: Any = None
    enter_exit: bool = False

    @validator('option')
    def _(cls, v, *, values) -> ParamMeta:
        if v is None:
            return None

        if v.param_decls:
            name, *_ = sorted(v.param_decls, key=lambda s: len(s), reverse=True)
        else:
            name = values['name']

        param = ParamMeta(name=name.strip('-'), default=v, annotation=str)
        click_param, _ = get_click_param(param)
        return click_param

    def setup(self, cli_input: Any=None, *, ctx: click.Context):
        r = self.to_call(cli_input, ctx=ctx)

        if self.enter_exit:
            r.__enter__()

    def close(self):
        ctx = click.get_current_context()
        r = getattr(ctx.obj, self.name)

        if self.enter_exit:
            r.__exit__(None, None, None)


def depends(option: Optional[O_]=None, enter_exit: bool=False, **kw):
    """
    Inject a dependency into the underlying command.
    """
    def _wrapper(f):
        if not hasattr(f, '_dependencies'):
            f._dependencies = []

        for k, v in kw.items():
            d = Dependency(name=k, to_call=v, option=option, enter_exit=enter_exit)
            f._dependencies.append(d)

        return f

    return _wrapper


class DataTable(Table):
    """
    Extends rich's CLI-pretty Table.

    Feed DataTable data, and we'll render it prettily.
    """
    def __init__(
        self,
        data: List[Dict[str, Any]],
        limit: int = 6,
        **table_kw
    ):
        super().__init__(*data[0].keys(), **table_kw)
        self.data = data
        self.limit = limit

        if len(self.data) > self.limit:
            top  = self.data[: self.limit // 2]
            mid  = [{_: '...' for _ in self.data[0]}]
            bot  = self.data[-1 * self.limit // 2:]
            data = [*top, *mid, *bot]
        else:
            data = self.data

        for row in data:
            self.add_row(*row.values())

#


RE_CLICK_SPECIFIER = re.compile(r'\[(.+)\]')
RE_REQUIRED = re.compile(r'\(.*(?P<tok>required).*\)')
RE_ENVVAR = re.compile(r'\(.*env var: (?P<tok>.*?)(?:;|\))')
RE_DEFAULT = re.compile(r'\(.*(?P<tok>default:) .*?\)')
console = Console(theme=CONSOLE_THEME)


def frontend(f: Callable) -> Callable:
    """
    Decorator that adds frontend-specific command args.
    """
    param_info = {
        'config': {
            'type': str,
            'arg': O_(None, help='~! config file identifier', hidden=True)
        },
        'host': {
            'type': str,
            'arg': O_(None, help='~! thoughtspot server', hidden=True)
        },
        'port': {
            'type': int,
            'arg': O_(None, help='~! optional, port of the thoughtspot server', hidden=True)
        },
        'username': {
            'type': str,
            'arg': O_(None, help='~! username when logging into ThoughtSpot', hidden=True)
        },
        'password': {
            'type': str,
            'arg': O_(None, help='~! password when logging into ThoughtSpot', hidden=True)
        },
        'temp_dir': {
            'type': pathlib.Path,
            'arg': O_(
                None,
                '--temp_dir',
                help='~! location on disk to save temporary files',
                file_okay=False,
                resolve_path=True,
                hidden=True,
                show_default=False
            )
        },
        'disable_ssl': {
            'type': bool,
            'arg': O_(
                None,
                '--disable_ssl',
                help='~! disable SSL verification',
                hidden=True,
                show_default=False
            )
        },
        'disable_sso': {
            'type': bool,
            'arg': O_(
                None,
                '--disable_sso',
                help='~! disable automatic SAML redirect',
                hidden=True,
                show_default=False
            )
        },
        'verbose': {
            'type': bool,
            'arg': O_(
                None,
                '--verbose',
                help='~! enable verbose logging for this run only',
                hidden=True,
                show_default=False
            )
        }
    }

    params = [
        Parameter(n, kind=Parameter.KEYWORD_ONLY, default=i['arg'], annotation=i['type'])
        for n, i in param_info.items()
    ]

    # construct a signature from f, add additional arguments.
    orig = Signature.from_callable(f)
    args = [p for n, p in orig.parameters.items() if n != 'frontend_kw']
    sig = orig.replace(parameters=(*args, *params))
    f.__signature__ = sig
    return f


def show_error(error: UsageError):
    """
    Show an error on the CLI.
    """
    msg = ''

    if error.ctx is not None:
        msg = error.ctx.get_usage()

        if error.ctx.command.get_help_option(error.ctx) is not None:
            msg += (
                f'\n[warning]Try \'{error.ctx.command_path} '
                f'{error.ctx.help_option_names[0]}\' for help.[/]'
            )

    msg += f'\n\n[error]Error: {error.format_message()}[/]'
    console.print(msg)


def show_full_help(ctx: click.Context, param: click.Parameter, value: str):
    """
    Show help.

    If --helpfull is passed, show all parameters, even if they're
    normally hidden.
    """
    ctx = click.get_current_context()

    if '--helpfull' in click.get_os_args():
        for param in ctx.command.params:
            if param.name == 'private':
                continue
            if 'backwards-compat' in param.help:
                continue

            param.hidden = False
            param.show_envvar = True

    if value and not ctx.resilient_parsing:
        console.print(ctx.get_help())
        raise typer.Exit()


def show_version(ctx: click.Context, param: click.Parameter, value: str):
    """
    Show version.
    """
    args = click.get_os_args()

    if '--version' not in args:
        return

    # top-level --version command
    if len(args) <= 2:
        version = __version__
        name = 'cs_tools'
    else:
        # either ..
        # ['tools', 'rtql', '--version']
        # or..
        # ['tools', 'rtql', 'interactive', '--version']
        # but both mean the same thing
        group, *cmds, _ = args
        name, *_ = cmds

        if group != 'tools':
            console.print('[b red]--version is not available for this command')
            raise typer.Exit(-1)

        for path in (PACKAGE_DIR / 'tools').iterdir():
            if path.name.endswith(name):
                tool = CSTool(path)
                version = tool.version
                name = tool.name
                break

    console.print(f'{name} ({version})')
    raise typer.Exit()


def prettify_params(params: List[str], *, default_prefix: str='~!'):
    """
    Sort command options in the help menu.

    Options:
      --options native to the command
      --default options
      --help

    Each set of options will be ordered as well, with required options being
    sent to the top of the list.
    """
    options = []
    default = []

    for option, help_text in params:
        if help_text.startswith(default_prefix):
            help_text = help_text[len(default_prefix):].lstrip()
            target = default
        else:
            target = options

        # rich and typer/click don't play nicely together.
        # - rich's color spec is square-braced
        # - click's default|required spec is square-braced
        #
        # if a command has a default or required option, rich thinks it's part
        # of the color spec and will swallow it. So we'll convert click's spec
        # from [] to () to fix that.

        # match options
        matches = RE_CLICK_SPECIFIER.findall(option)

        if matches:
            for match in matches:
                option = option.replace(f'[{match}]', f'[info]({match})[/]')

        # match options' help text
        matches = RE_CLICK_SPECIFIER.findall(help_text)

        if matches:
            for match in matches:
                help_text = help_text.replace(f'[{match}]', f'[info]({match})[/]')

        # highlight environment variables in warning color
        match = RE_ENVVAR.search(help_text)

        if match:
            match = match.group('tok')
            help_text = help_text.replace(match, f'[warning]{match}[/]')

        # highlight defaults in green color
        match = RE_DEFAULT.search(help_text)

        if match:
            match = match.group('tok')
            help_text = help_text.replace(match, f'[green]{match}[/]')

        # highlight required in error color
        match = RE_REQUIRED.search(help_text)

        if match:
            match = match.group('tok')
            help_text = help_text.replace(match, f'[error]{match}[/]')

        to_add = (option, help_text)
        getattr(target, 'append')(to_add)

    return [*options, *default]


VERSION_OPT = click.Option(
    ['--version'],
    is_flag=True,
    is_eager=True,
    expose_value=False,
    callback=show_version,
    help="Show the version and exit."
)


class CSToolsCommand(click.Command):
    """
    """
    def __init__(self, **kw):
        self._the_callback = cb = kw.pop('callback')
        self._dependencies = getattr(cb, '_dependencies', [])

        if kw['options_metavar'] == '[OPTIONS]':
            kw['options_metavar'] = '[--option, ..., --help]'

        [kw['params'].append(d.option) for d in self._dependencies if d.option]
        super().__init__(**kw, callback=self.callback_with_dependency_injection)

    def callback_with_dependency_injection(self, *a, **kw):
        kw['ctx'] = ctx = click.get_current_context()
        ctx.ensure_object(util.State)
        ctx.call_on_close(self.teardown)

        for _ in self._dependencies:
            if _.option is not None:
                value = kw.pop(_.option.name)
            else:
                value = kw.get(_.option.name)

            _.setup(cli_input=value, ctx=ctx) 

        return self._the_callback(*a, **kw)

    def teardown(self):
        for dependency in self._dependencies:
            if dependency.enter_exit:
                dependency.close()

    # OVERRIDES

    def parse_args(self, ctx: click.Context, args: List[str]) -> List[str]:
        try:
            super().parse_args(ctx, args)
        except UsageError as e:
            show_error(e)
            raise typer.Exit(-1)

    def get_params(self, ctx: click.Context) -> List[click.Parameter]:
        rv = self.params
        help_option = self.get_help_option(ctx)
        help_full_option = self.get_full_help_option(ctx)

        if help_option is not None:
            rv = [*rv, help_full_option, help_option]

        return rv

    def get_help(self, ctx: click.Context) -> str:
        """
        Formats the help into a string and returns it.
        """
        formatter = ctx.make_formatter()
        self.format_help(ctx, formatter)

        with console.capture() as c:
            console.print(formatter.getvalue().rstrip())

        return c.get()

    def format_help(self, ctx: click.Context, formatter: click.HelpFormatter) -> None:
        """
        Writes the help into the formatter if it exists.
        """
        formatter.write('\n')
        self.format_usage(ctx, formatter)
        self.format_help_text(ctx, formatter)
        self.format_arguments(ctx, formatter)
        self.format_options(ctx, formatter)
        self.format_epilog(ctx, formatter)

    def format_arguments(self, ctx, formatter):
        arguments = []

        for param in self.get_params(ctx):
            r = param.get_help_record(ctx)

            if r is not None:
                if isinstance(param, click.Argument):
                    arguments.append(r)

        if arguments:
            arguments = prettify_params(arguments)

            with formatter.section('Arguments'):
                formatter.write_dl(arguments)

    def format_options(self, ctx, formatter):
        options = []

        for p in self.get_params(ctx):
            r = p.get_help_record(ctx)

            if r is not None and isinstance(p, click.Option):
                options.append(r)

        if options:
            *params, help_full, help_ = options

            if click.get_os_args()[0] == 'tools':
                options = [*prettify_params(params), help_full, help_]
            else:
                options = [*prettify_params(params), help_]

            with formatter.section('Options'):
                formatter.write_dl(options)

    # EXTRA METHODS

    def get_full_help_option(self, ctx: click.Context) -> Optional[click.Option]:
        """
        Returns the help option object.
        """
        return click.Option(
            ['--helpfull'],
            is_flag=True,
            is_eager=True,
            expose_value=False,
            callback=show_full_help,
            help=('Show the full help message and exit.')
        )


class CSToolsGroup(click.Group):
    """
    """

    def __init__(self, **kw):
        if kw['options_metavar'] == '[OPTIONS]':
            kw['options_metavar'] = '[--help]'

        if kw['subcommand_metavar'] is None:
            kw['subcommand_metavar'] = '<command>'

        kw['no_args_is_help'] = True
        super().__init__(**kw)

    # OVERRIDES

    def parse_args(self, ctx: click.Context, args: List[str]) -> List[str]:

        try:
            super().parse_args(ctx, args)
        except UsageError as e:
            show_error(e)
            raise typer.Exit(-1)

    def get_help(self, ctx: click.Context) -> str:
        """
        Formats the help into a string and returns it.
        """
        formatter = ctx.make_formatter()
        self.format_help(ctx, formatter)

        with console.capture() as c:
            console.print('\n', formatter.getvalue().rstrip())

        return c.get()

    def get_params(self, ctx: click.Context) -> List[click.Parameter]:
        rv = self.params
        help_option = self.get_help_option(ctx)
        version_option = self.get_version_option(ctx)

        args = click.get_os_args()

        if (
            not args                                 # cs_tools
            or args[0].startswith('--')              # cs_tools --version
            or args[0] == 'tools' and len(args) > 1  # cs_tools tools * --version
        ):
            rv = [*rv, version_option]

        if help_option is not None:
            rv = [*rv, help_option]

        return rv

    def format_commands(self, ctx: click.Context, formatter: click.HelpFormatter) -> None:
        """
        Extra format methods for multi methods that
        adds all the commands after the options.

        Nearly direct copy from source:
            https://github.com/pallets/click/blob/main/src/click/core.py#L1571

        ... with the only change being the section name change (at the end of
        this method), to "Tools" instead of "Commands"
        """
        commands = []
        for subcommand in self.list_commands(ctx):
            cmd = self.get_command(ctx, subcommand)
            # What is this, the tool lied about a command.  Ignore it
            if cmd is None:
                continue
            if cmd.hidden:
                continue

            commands.append((subcommand, cmd))

        # allow for 3 times the default spacing
        if len(commands):
            limit = formatter.width - 6 - max(len(cmd[0]) for cmd in commands)

            rows = []
            for subcommand, cmd in commands:
                help = cmd.get_short_help_str(limit)
                rows.append((subcommand, help))

            if rows:
                args = click.get_os_args()

                if args == ['tools'] or args == ['tools', '--help']:
                    section = 'Tools'
                else:
                    section = 'Commands'

                with formatter.section(section):
                    formatter.write_dl(rows)

    # EXTRA METHODS

    def get_version_option(self, ctx: click.Context) -> Optional[click.Option]:
        """
        Returns the version option.
        """
        return click.Option(
            ['--version'],
            is_flag=True,
            is_eager=True,
            expose_value=False,
            callback=show_version,
            help="Show the version and exit."
        )


def _csv(ctx: click.Context, param: click.Parameter, value: Tuple[str]) -> List[str]:
    """
    Convert arguments to a list of strings.

    Arguments can be supplied on the CLI like..

      --tables table1,table2 --tables table3

    ..and will output as a flattened list of strings.

      ['table1', 'table2', 'table3']
    """
    return list(it.chain.from_iterable([v.split(',') for v in value]))
