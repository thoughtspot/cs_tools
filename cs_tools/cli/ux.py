from typing import Any, List, Optional, Tuple
import logging
import sys

from click.exceptions import UsageError
from rich.console import Console
from click.core import iter_params_for_processing
from gettext import ngettext
import click

from cs_tools.cli.loader import CSTool
from cs_tools.const import CONSOLE_THEME
from cs_tools import __version__


log = logging.getLogger(__name__)
console = Console(theme=CONSOLE_THEME)


class CSToolsPrettyMixin:
    """
    Handles core formatting that are common to both Commands and Groups.
    """
    # context_class = CSToolsContext
    from typing import Sequence

    def main(self, **passthru) -> Any:
        """
        This is the way to invoke a script with all the bells and
        whistles as a command line application. This will always
        terminate the application after a call.

        We override this in CS Tools to prevent "standalone mode". In
        standalone mode, Click will then handle exceptions and convert
        them into error messages. If this is set to `False`, errors
        will be propagated to the caller.

        We WANT errors to propogate in this case, because in CS Tools,
        we are overriding the default stdout printer to allow for pretty
        color to be included. :)
        """
        try:
            try:
                return super().main(**passthru, standalone_mode=False)
            except (click.Abort, KeyboardInterrupt):
                console.print('[yellow]You cancelled the currently running command..')
            except click.UsageError as e:
                self.show_error_and_exit(e)

        except click.exceptions.Exit as e:
            raise SystemExit(e.exit_code)

    def help_in_args(self, ctx: click.Context, *, args: List[str] = None) -> bool:
        """
        Determine if any variation of --help was given.
        """
        if args is None:
            args = sys.argv[1:]

        return set(ctx.help_option_names).intersection(set(args))

    def show_help_and_exit(
        self,
        ctx: click.Context,
        param: click.Parameter = None,
        value: bool = None
    ) -> None:
        """
        Show help, then exit.

        If --helpfull is passed, show and colorize hidden options.
        """
        if '--helpfull' in sys.argv[1:]:
            cs_tools_variant, _, _ = ctx.command_path.partition(' ')

            for p in ctx.command.params:
                # truly hidden options
                if f'{ctx.command_path} --{p.name}' in (
                    f'{cs_tools_variant} tools --private',
                    f'{cs_tools_variant} tools --beta',
                ):
                    continue

                # colorize revealed options
                if p.hidden:
                    p.help = f'[yellow3]{p.help}[/]'

                p.hidden = False
                p.show_envvar = True

        console.print(ctx.get_help())
        ctx.exit()

    def show_error_and_exit(self, error: click.ClickException) -> None:
        """
        Show error, then exit.
        """
        ctx = error.ctx

        if error.ctx is not None:
            msg = error.ctx.get_usage()

            if error.ctx.command.get_help_option(error.ctx) is not None:
                msg += (
                    f"\n[b yellow]Try '[b cyan]{error.ctx.command_path} "
                    f"{error.ctx.help_option_names[0]}[/]' for help.[/]"
                )

        msg += f'\n\n[red1]Error: {error.format_message()}[/]'
        console.print(msg)
        ctx.exit(-1)

    def parse_args(self, ctx: click.Context, args: List[str]) -> List[str]:
        if not args and self.no_args_is_help and not ctx.resilient_parsing:
            self.show_help_and_exit(ctx)

        if set(args).issubset(self.get_help_option_names(ctx)):
            self.show_help_and_exit(ctx)

        try:
            r = super().parse_args(ctx, args)
        except UsageError as e:
            self.show_error_and_exit(e)

        return r

    def format_rich(self, option_name: str, option_help: str) -> Tuple[str, str]:
        """
        Adds some color to --options with the help of rich.

        Required options will be annotated with some RED.
        Defaulted options will be annotated with some YELLOW & GREEN.
        """
        if '[required]' in option_help:
            option_help.replace('[required]', r'[red]\[required][/]')

        if '[default: ' in option_help:
            option_help, _, default_value = option_help[:-1].partition('[default: ')
            option_help += fr'[yellow3]\[default: [green1]{default_value}[/]][/]'

        return (option_name, option_help)

    def format_usage(self, ctx: click.Context, formatter: click.HelpFormatter) -> None:
        """
        Writes the usage line into the formatter.

        Adds some color to the usage text with the help of rich.
        """
        pieces = self.collect_usage_pieces(ctx)
        args = ' '.join(pieces)
        formatter.write_usage(f'[cyan][b]{ctx.command_path}[/][/]', f'[cyan]{args}[/]')

    def format_options(self, ctx: click.Context, formatter: click.HelpFormatter) -> None:
        """
        Writes all the options into the formatter if they exist.

        Adds some color to the options text with the help of rich.
        """
        options = []

        for p in self.get_params(ctx):
            r = p.get_help_record(ctx)

            if r is not None and isinstance(p, click.Option):
                options.append(r)

        if options:
            *params, (help_names, help_desc) = options
            help_names = sorted(help_names.split(', '), key=len)
            help_ = (', '.join(help_names), help_desc)
            options = [*(self.format_rich(*p) for p in params), help_]

            with formatter.section('Options'):
                formatter.write_dl(options)


class CSToolsCommand(CSToolsPrettyMixin, click.Command):
    """
    """

    def __init__(self, **kw):
        self.dependencies = getattr(kw['callback'], 'dependencies', [])
        self._extra_params = [o for d in self.dependencies for o in (d.options or [])]
        kw['params'].extend(self._extra_params)

        if kw['options_metavar'] == '[OPTIONS]':
            metavar = ''

            if any(1 for _ in kw['params'] if _.name == 'config'):
                metavar += '--config IDENTIFIER '

            metavar += '[--option, ..., --help]'
            kw['options_metavar'] = metavar

        super().__init__(**kw)
        self.no_args_is_help = True  # override

    # ADDITIONAL METHODS

    def _setup_dependencies(self, ctx, opts):
        ctx.call_on_close(self._teardown_dependencies)

        for dependency in self.dependencies:
            overrides = {}

            for k, v in opts.items():
                if k in [o.name for o in dependency.options]:
                    overrides[k] = v

            _: Any = dependency.setup(ctx, **overrides)

    def _teardown_dependencies(self):
        ctx = click.get_current_context()

        for dependency in self.dependencies:
            try:
                dependency.terminate(ctx)
            except Exception as e:
                log.debug(e, exc_info=True)
                log.warning(f'error while tearing down dependency: {dependency.name}')

    def format_arguments(self, ctx: click.Context, formatter: click.HelpFormatter) -> None:
        """
        Writes all the arguments into the formatter if they exist.

        Adds some color to the options text with the help of rich.
        """
        arguments = []

        for param in self.get_params(ctx):
            r = param.get_help_record(ctx)

            if r is not None and isinstance(param, click.Argument):
                arguments.append(r)

        if arguments:
            # arguments = prettify_params(arguments)

            with formatter.section('Arguments'):
                formatter.write_dl(arguments)

    # INHERITANCE OVERRIDES

    def parse_args(self, ctx: click.Context, args: List[str]) -> List[str]:
        """
        """
        if self.help_in_args(ctx, args=args):
            self.show_help_and_exit(ctx)

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
            self.show_error_and_exit(e)

        ctx.args = args
        return args

    def format_help(self, ctx: click.Context, formatter: click.HelpFormatter) -> None:
        """
        Writes the help into the formatter if it exists.

        This is a low-level method called by self.get_help().

        This calls the following methods:
          - self.format_usage()
          - self.format_help_text()
          - self.format_arguments()
          - self.format_options()
          - self.format_epilog()
        """
        self.format_usage(ctx, formatter)
        self.format_help_text(ctx, formatter)
        self.format_arguments(ctx, formatter)
        self.format_options(ctx, formatter)
        self.format_epilog(ctx, formatter)


class CSToolsGroup(CSToolsPrettyMixin, click.Group):
    """
    Represent a CS Tools multi-command.

    CS Tools are each defined as a module within the larger cs_tools.cli
    package. Each tool represents a specific domain, bundling commands
    together.
    """
    command_class = CSToolsCommand
    group_class = type

    def __init__(self, **kw):
        kw['options_metavar'].replace('[OPTIONS]', '[--help]')
        kw['subcommand_metavar'] = kw.get('subcommand_metavar', '<command>')
        super().__init__(**kw)
        self.no_args_is_help = True  # override

    # ADDITIONAL OPTIONS

    def get_version_option(self, ctx: click.Context) -> Optional[click.Option]:
        """
        Returns the version option.

        --version is only allowed on top-level cs_tools and tools themselves.
        """
        return click.Option(
            ['--version'],
            is_flag=True,
            is_eager=True,
            expose_value=False,
            callback=self.show_version_and_exit,
            help="Show the version and exit."
        )

    # ADDITIONAL METHODS

    def show_version_and_exit(
        self,
        ctx: click.Context,
        param: click.Parameter = None,
        value: bool = None
    ) -> None:
        """
        Show version and exit.

        In CS Tools, only the top-level CLI object, as well as individual tools
        themselves will have a version number attached. These are both
        represented as a click.Group.
        """
        if not value:
            return

        args = sys.argv[1:]

        # --help is the universal override
        if self.help_in_args(ctx, args=args):
            self.show_help_and_exit(ctx)

        cs_tools_variant, _, _ = ctx.command_path.partition(' ')

        if f'{ctx.command_path} --version' in (
            f'{cs_tools_variant} tools --version',
            f'{cs_tools_variant} --version',
        ):
            name = 'cs_tools'
            version = __version__

        # cs_tools tools <tool> --version
        if len(args) > 2:
            _, tool_name, *_ = args
            tool = ctx.obj.tools[tool_name]
            name = f'cs_tools {tool.name}'
            version = tool.version

        console.print(f'{name} ({version})')
        ctx.exit(0)

    # INHERITANCE OVERRIDES

    def get_params(self, ctx: click.Context) -> List[click.Parameter]:
        # this is called by click.. in cli, in execution order
        # 1. Command.make_parser
        # 2. BaseCommand.parse_args
        # 3. Context.make_parser
        rv = self.params
        help_option = self.get_help_option(ctx)

        # this block decides when we include the --version option
        if ' '.join(sys.argv[1:]) in (
            '', '--version', '--help',  # aka top-level commands
            f'tools {next(iter(sys.argv[-2:]), 0)} --version',
            f'tools {next(iter(sys.argv[-2:]), 0)} --help',
        ):
            version_option = self.get_version_option(ctx)
            rv = [*rv, version_option]

        # --help option should always be last in the list
        if help_option is not None:
            rv = [*rv, help_option]

        return rv

    def format_options(self, ctx: click.Context, formatter: click.HelpFormatter) -> None:
        """
        Writes all the options into the formatter if they exist.

        But also call .format_commands()
        """
        super().format_options(ctx, formatter)
        self.format_commands(ctx, formatter)

    def format_commands(self, ctx: click.Context, formatter: click.HelpFormatter) -> None:
        """
        Extra format methods for multi methods that adds all the
        commands after the options.

        Nearly direct copy from source:
          https://github.com/pallets/click/blob/main/src/click/core.py#L1571

        Changes include:
          - reassignment of section name from Commands --> Tools
          - inclusion of all possible help optoin names
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
        if commands:
            limit = formatter.width - 6 - max(len(cmd[0]) for cmd in commands)
            rows = []

            for subcommand, cmd in commands:
                help = cmd.get_short_help_str(limit)
                rows.append((subcommand, help))

            if rows:
                if ' '.join(sys.argv[1:]) in (
                    'tools',
                    *(f'tools {help_opt}' for help_opt in ctx.help_option_names)
                ):
                    section = 'Tools'
                else:
                    section = 'Commands'

                with formatter.section(section):
                    formatter.write_dl(rows)
