from inspect import Signature, Parameter
from typing import Any, Callable, Dict, List, Optional, Tuple
import itertools as it
import re

from click.exceptions import UsageError
from rich.console import Console
from rich.table import Table
from click.core import iter_params_for_processing
from click import Parameter as Parameter_, Option, Context, HelpFormatter
from typer import Argument as A_, Option as O_
import typer
import click

from cs_tools.helpers.loader import CSTool
from cs_tools.const import CONSOLE_THEME, PACKAGE_DIR
from cs_tools import __version__


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


# NOTE:
#
#   click dependent version (>=7.1.2, <8.0.0), does not yet support proper subclassing
#   of Command and Group. There's a lot of duplication below, but it's necessary in
#   order to achieve the user experience we want.
#
#   In click >= 8.0.0, we can set the command and group subclass types like..
#
#   class RichGroup(click.Group):
#       command_class = RichCommand
#       group_class = type
#
#   ..and remove all the code duplication in RichGroup.
#
#   Also, the reason why we're on click ^7.1.2 is because typer has not yet been updated
#   to use click 8.0.0
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
        'disable_ssl': {
            'type': bool,
            'arg': O_(None, '--disable_ssl', help='~! disable SSL verification', hidden=True)
        },
        'disable_sso': {
            'type': bool,
            'arg': O_(None, '--disable_sso', help='~! disable automatic SAML redirect', hidden=True)
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


def show_error(e: UsageError):
    """
    Show an error on the CLI.
    """
    ctx = e.ctx
    msg = ''

    if ctx is not None:
        msg = f'{ctx.get_usage()}'

        if ctx.command.get_help_option(ctx) is not None:
            msg += (
                f'\n[warning]Try \'{ctx.command_path} '
                f'{ctx.help_option_names[0]}\' for help.[/]'
            )

    msg += f'\n\n[error]Error: {e.format_message()}[/]'
    console.print(msg)


def show_full_help(ctx: Context, param: Parameter_, value: str):
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

            param.hidden = False
            param.show_envvar = True

    if value and not ctx.resilient_parsing:
        console.print(f'{ctx.get_help()}')
        raise typer.Exit()


def show_version(ctx: Context, param: Parameter, value: str):
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

    console.print(f'[white]{name} ({version})')
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


class RichCommand(click.Command):
    """
    Allow Commands to use the rich interface.
    """
    def get_params(self, ctx: Context) -> List[Parameter_]:
        rv = self.params
        help_option = self.get_help_option(ctx)
        help_full_option = self.get_full_help_option(ctx)

        if help_option is not None:
            rv = [*rv, help_full_option, help_option]

        return rv

    def get_help_option(self, ctx: Context) -> Optional[Option]:
        """
        Returns the help option object.
        """
        help_options = self.get_help_option_names(ctx)

        if not help_options or not self.add_help_option:
            return None

        return Option(
            help_options,
            is_flag=True,
            is_eager=True,
            expose_value=False,
            callback=show_full_help,
            help=('Show this message and exit.')
        )

    def get_full_help_option(self, ctx: Context) -> Optional[Option]:
        """
        Returns the help option object.
        """
        return Option(
            ['--helpfull'],
            is_flag=True,
            is_eager=True,
            expose_value=False,
            callback=show_full_help,
            help=('Show the full help message and exit.')
        )

    def get_help(self, ctx: Context) -> str:
        """
        Formats the help into a string and returns it.
        """
        formatter = ctx.make_formatter()
        self.format_help(ctx, formatter)
        return formatter.getvalue()

    def format_help(self, ctx: Context, formatter: HelpFormatter) -> None:
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

        for param in self.get_params(ctx):
            r = param.get_help_record(ctx)

            if r is not None:
                if isinstance(param, click.Option):
                    options.append(r)

        if options:
            *params, help_full, help_ = options
            options = prettify_params(params)

            if '--helpfull' in click.get_os_args():
                options = [*options, help_]
            elif ctx.info_name == ctx.command_path:
                options = [*options, help_]
            elif 'logs' in click.get_os_args() or 'config' in click.get_os_args():
                options = [*options, help_]
            else:
                options = [*options, help_full, help_]

            with formatter.section('Options'):
                formatter.write_dl(options)

    def parse_args(self, ctx: Context, args: List[str]) -> List[str]:

        if not args and self.no_args_is_help and not ctx.resilient_parsing:
            show_full_help(ctx, None, True)
            raise typer.Exit()

        parser = self.make_parser(ctx)

        try:
            opts, args, param_order = parser.parse_args(args=args)
        except UsageError as e:
            show_error(e)
            raise typer.Exit(-1)

        for param in iter_params_for_processing(param_order, self.get_params(ctx)):
            value, args = param.handle_parse_result(ctx, opts, args)

        if args and not ctx.allow_extra_args and not ctx.resilient_parsing:
            s = '' if len(args) == 1 else 's'
            args = ' '.join(args)
            console.print(f'[error]Got unexpected extra argument{s} ({args})[/]')
            raise typer.Exit(code=1)

        ctx.args = args
        return args


class RichGroup(click.Group):
    """
    Allow Groups to use the rich interface.
    """
    def get_params(self, ctx: Context) -> List[Parameter_]:
        rv = self.params
        help_option = self.get_help_option(ctx)
        help_full_option = self.get_full_help_option(ctx)
        version_option = self.get_version_option(ctx)

        # top-level commands
        if ctx.command_path.endswith(('config', 'tools', 'logs')):
            version_option.hidden = True

        if version_option is not None:
            rv = [*rv, version_option]

        if help_option is not None:
            rv = [*rv, help_full_option, help_option]

        return rv

    def get_help_option(self, ctx: Context) -> Optional[Option]:
        """
        Returns the help option object.
        """
        help_options = self.get_help_option_names(ctx)

        if not help_options or not self.add_help_option:
            return None

        return Option(
            help_options,
            is_flag=True,
            is_eager=True,
            expose_value=False,
            callback=show_full_help,
            help=('Show this message and exit.')
        )

    def get_full_help_option(self, ctx: Context) -> Optional[Option]:
        """
        Returns the help option object.
        """
        return Option(
            ['--helpfull'],
            is_flag=True,
            is_eager=True,
            expose_value=False,
            callback=show_full_help,
            help=('Show the full help message and exit.')
        )

    def get_version_option(self, ctx: Context) -> Optional[Option]:
        """
        Returns the help option object.
        """
        return Option(
            ['--version'],
            is_flag=True,
            is_eager=True,
            expose_value=False,
            callback=show_version,
            help=('Show the tool\'s version and exit.')
        )

    def get_help(self, ctx: Context) -> str:
        """
        Formats the help into a string and returns it.
        """
        formatter = ctx.make_formatter()
        self.format_help(ctx, formatter)
        return formatter.getvalue()

    def format_help(self, ctx: Context, formatter: HelpFormatter) -> None:
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

        for param in self.get_params(ctx):
            r = param.get_help_record(ctx)

            if r is not None:
                if isinstance(param, click.Option):
                    options.append(r)

        if options:
            *params, help_full, help_ = options
            options = prettify_params(params)

            if '--helpfull' in click.get_os_args():
                options = [*options, help_]
            elif ctx.info_name == ctx.command_path:
                options = [*options, help_]
            elif 'logs' in click.get_os_args() or 'config' in click.get_os_args():
                options = [*options, help_]
            else:
                options = [*options, help_full, help_]

            with formatter.section('Options'):
                formatter.write_dl(options)

        # NOTE: during refactor, do not delete!
        self.format_commands(ctx, formatter)

    def _parse_args(self, ctx: Context, args: List[str]) -> List[str]:
        if not args and self.no_args_is_help and not ctx.resilient_parsing:
            show_full_help(ctx, None, True)
            raise typer.Exit()

        parser = self.make_parser(ctx)

        try:
            opts, args, param_order = parser.parse_args(args=args)
        except UsageError as e:
            show_error(e)
            raise typer.Exit(-1)

        for param in iter_params_for_processing(param_order, self.get_params(ctx)):
            value, args = param.handle_parse_result(ctx, opts, args)

        if args and not ctx.allow_extra_args and not ctx.resilient_parsing:
            s = '' if len(args) == 1 else 's'
            args = ' '.join(args)
            console.print(f'[error]Got unexpected extra argument{s} ({args})[/]')
            raise typer.Exit(code=1)

        ctx.args = args
        return args

    def parse_args(self, ctx: Context, args: List[str]) -> List[str]:
        if not args and self.no_args_is_help and not ctx.resilient_parsing:
            show_full_help(ctx, None, True)
            raise typer.Exit()

        rest = self._parse_args(ctx, args)

        if self.chain:
            ctx.protected_args = rest
            ctx.args = []
        elif rest:
            ctx.protected_args, ctx.args = rest[:1], rest[1:]

        return ctx.args


def _csv(ctx: Context, param: Parameter_, value: Tuple[str]) -> List[str]:
    """
    Convert arguments to a list of strings.

    Arguments can be supplied on the CLI like..

      --tables table1,table2 --tables table3

    ..and will output as a flattened list of strings.

      ['table1', 'table2', 'table3']
    """
    return list(it.chain.from_iterable([v.split(',') for v in value]))
