from typing import List, Tuple, Optional
import itertools as it
import datetime as dt
import logging
import sys
import re

from click.exceptions import UsageError
from rich.console import Console
from click.core import iter_params_for_processing
from gettext import ngettext
import pendulum
import typer
import click
import toml

from cs_tools.sync.protocol import SyncerProtocol
from cs_tools.cli._loader import CSTool
from cs_tools.const import CONSOLE_THEME, PACKAGE_DIR
from cs_tools.data import models
from cs_tools.sync import register
from cs_tools.util import State
from cs_tools import __version__


log = logging.getLogger(__name__)
RE_CLICK_SPECIFIER = re.compile(r'\[(.+)\]')
RE_REQUIRED = re.compile(r'\(.*(?P<tok>required).*\)')
RE_ENVVAR = re.compile(r'\(.*env var: (?P<tok>.*?)(?:;|\))')
RE_DEFAULT = re.compile(r'\(.*(?P<tok>default:) .*?\)')
console = Console(theme=CONSOLE_THEME)


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

        if definition == 'default':
            ts_config = ctx.obj.thoughtspot.config
            try:
                definition = ts_config.syncer[proto]
            except (TypeError, KeyError):
                log.error(f'[error]no default found for syncer protocol: [blue]{proto}')
                raise typer.Exit(-1)

        cfg = toml.load(definition)

        if 'manifest' not in cfg:
            cfg['manifest'] = PACKAGE_DIR / 'sync' / proto / 'MANIFEST.json'

        log.info(f'registering syncer: {proto}')
        Syncer = register.load_syncer(protocol=proto, manifest_path=cfg.pop('manifest'))

        # sanitize input by accepting aliases
        if hasattr(Syncer, '__pydantic_model__'):
            cfg['configuration'] = Syncer.__pydantic_model__.parse_obj(cfg['configuration']).dict()

        syncer = Syncer(**cfg['configuration'])

        # don't actually make lasting changes, just ensure it initializes
        if validate_only:
            return value

        if getattr(syncer, '__is_database__', False):
            models.SQLModel.metadata.create_all(syncer.cnxn)

        return syncer


#


def show_version(ctx: click.Context, param: click.Parameter, value: str):
    """
    Show version.
    """
    args = sys.argv[1:]

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

        for path in (PACKAGE_DIR / 'cli' / 'tools').iterdir():
            if path.name.endswith(name):
                tool = CSTool(path)
                version = tool.version
                name = tool.name
                break

    console.print(f'{name} ({version})')
    raise typer.Exit()


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

    if '--helpfull' in sys.argv[1:]:
        for p in ctx.command.params:
            if p.name == 'private':
                continue
            if 'backwards-compat' in p.help:
                continue

            p.hidden = False
            p.show_envvar = True

    if value and not ctx.resilient_parsing:
        console.print(ctx.get_help())
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


class CSToolsPrettyMixin:

    def get_help(self, ctx: click.Context) -> str:
        """
        Formats the help into a string and returns it.
        """
        formatter = ctx.make_formatter()
        self.format_help(ctx, formatter)

        with console.capture() as c:
            console.print(formatter.getvalue().rstrip())

        return c.get()

    def format_options(self, ctx, formatter):
        options = []

        for p in self.get_params(ctx):
            r = p.get_help_record(ctx)

            if r is not None and isinstance(p, click.Option):
                options.append(r)

        if options:
            *params, (help_names, help_desc) = options
            help_names = sorted(help_names.split(', '), key=len)
            help_ = (', '.join(help_names), help_desc)
            options = [*prettify_params(params), help_]

            with formatter.section('Options'):
                formatter.write_dl(options)


class CSToolsCommand(CSToolsPrettyMixin, click.Command):
    """
    """
    def __init__(self, **kw):
        self._dependencies = getattr(kw['callback'], '_dependencies', [])
        self._extra_params = [o for d in self._dependencies for o in (d.options or [])]
        kw['params'].extend(self._extra_params)

        if kw['options_metavar'] == '[OPTIONS]':
            metavar = ''

            if any(1 for _ in kw['params'] if _.name == 'config'):
                metavar += '--config IDENTIFIER '

            metavar += '[--option, ..., --help]'
            kw['options_metavar'] = metavar

        super().__init__(**kw)
        # self.no_args_is_help = True

    def _setup_dependencies(self, ctx, opts):
        ctx.ensure_object(State)
        ctx.call_on_close(self.teardown)

        for dep in self._dependencies:
            overrides = {}

            for k, v in opts.items():
                if k in [o.name for o in dep.options]:
                    overrides[k] = v

            dep.setup(ctx, **overrides)

    def teardown(self):
        for dependency in self._dependencies:
            if dependency.enter_exit:
                dependency.close()

    # OVERRIDES

    def parse_args(self, ctx: click.Context, args: List[str]) -> List[str]:
        """
        """
        if set(ctx.help_option_names).intersection(set(args)):
            show_full_help(ctx, None, True)

        try:
            parser = self.make_parser(ctx)
            opts, args, param_order = parser.parse_args(args=args)
            self._setup_dependencies(ctx, opts.copy())

            # remove extra params
            self.params = [p for p in self.params if p not in self._extra_params]

            for param in iter_params_for_processing(param_order, self.get_params(ctx)):
                value, args = param.handle_parse_result(ctx, opts, args)

            if args and not ctx.allow_extra_args and not ctx.resilient_parsing:
                ctx.fail(
                    ngettext(
                        "Got unexpected extra argument ({args})",
                        "Got unexpected extra arguments ({args})",
                        len(args),
                    ).format(args=" ".join(map(str, args)))
                )
        except UsageError as e:
            show_error(e)
            raise typer.Exit(-1)

        ctx.args = args
        return args

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


class CSToolsGroup(CSToolsPrettyMixin, click.Group):
    """
    """
    command_class = CSToolsCommand
    group_class = type

    def __init__(self, **kw):
        if kw['options_metavar'] == '[OPTIONS]':
            kw['options_metavar'] = '[--help]'

        if kw['subcommand_metavar'] is None:
            kw['subcommand_metavar'] = '<command>'

        super().__init__(**kw)
        self.no_args_is_help = True

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
        version_option = self.get_version_option(ctx)

        args = sys.argv[1:]

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
                args = sys.argv[1:]

                if args == ['tools'] or args == ['tools', '--help']:
                    section = 'Tools'
                else:
                    section = 'Commands'

                with formatter.section(section):
                    formatter.write_dl(rows)

    def format_options(self, ctx, formatter):
        super().format_options(ctx, formatter)
        self.format_commands(ctx, formatter)

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
