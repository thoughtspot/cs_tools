from typing import Any, List, Optional, Tuple
import logging
import sys

from click.exceptions import UsageError
from rich.console import Console
from click.core import iter_params_for_processing
import gevent
import click

from cs_tools.settings import _meta_config
from cs_tools.const import CONSOLE_THEME
from cs_tools import __version__


log = logging.getLogger(__name__)
console = Console(theme=CONSOLE_THEME)


class CSToolsContext(click.Context):
    """
    The context is a special internal object that holds state relevant for the
    script execution at every single level.  It's normally invisible to
    commands unless they opt-in to getting access to it.
    """

    def get_help(self) -> str:
        """
        Helper method to get formatted help page for the current context
        and command.

        Just tacking on a newline.
        """
        return self.command.get_help(self) + '\n'


class CSToolsPrettyMixin:
    """
    Handles core formatting that are common to both Commands and Groups.
    """
    context_class = CSToolsContext

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
        # gevent complains when users cancel running programs, but cs_tools shouldn't...
        gevent.get_hub().NOT_ERROR += (KeyboardInterrupt,)

        try:
            try:
                return super().main(**passthru, standalone_mode=False)
            except click.Abort:
                console.print('[hint]You cancelled the currently running command..\n')
            except click.UsageError as e:
                self.show_error_and_exit(e)

        except click.exceptions.Exit as e:
            raise SystemExit(e.exit_code)

    def help_cmd_or_no_input(self, args: List[str], *, ctx: click.Context) -> bool:
        """
        Identify cli inputs which require helptext.
        """
        help_in_args = set(args).issubset(self.get_help_option_names(ctx))
        no_input = not args and self.no_args_is_help
        tab_completion = ctx.resilient_parsing
        return help_in_args or (no_input and not tab_completion)

    def show_help_and_exit(
        self,
        ctx: click.Context,
        param: click.Parameter = None,
        value: bool = None
    ) -> None:
        """
        Show help, then exit.

        cs_tools additions:
          - if --helpfull is passed, show and colorize hidden options.
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
                    p.help = f'[hint]{p.help}[/]'

                p.hidden = False
                p.show_envvar = True

        console.print(ctx.get_help())
        ctx.exit(0)

    def show_error_and_exit(self, error: click.ClickException) -> None:
        """
        Show error, then exit.
        """
        ctx = error.ctx

        if error.ctx is not None:
            msg = error.ctx.get_usage()

            if error.ctx.command.get_help_option(error.ctx) is not None:
                msg += (
                    f"\n[hint]Try '[primary]{error.ctx.command_path} "
                    f"{error.ctx.help_option_names[0]}[/]' for help.[/]"
                )

        msg += f'\n\n[error]Error: {error.format_message()}[/]'
        console.print(msg + '\n')
        ctx.exit(-1)

    def parse_args(self, ctx: click.Context, args: List[str]) -> List[str]:
        """
        Base case for argument parsing.

        cs_tools additions:
          - introduce the standard help and error messages.
        """
        if self.help_cmd_or_no_input(args, ctx=ctx):
            self.show_help_and_exit(ctx)

        try:
            r = super().parse_args(ctx, args)
        except UsageError as e:
            self.show_error_and_exit(e)

        return r

    def format_rich(self, option_name: str, option_help: str) -> Tuple[str, str]:
        """
        Adds some color to --options with the help of rich.

        cs_tools additions:
          - required options will be annotated with some ARG | REQUIRED.
          - defaulted options will be annotated with some HINT & SECONDARY.
        """
        option_name = option_name.replace('[', r'\[')

        if '[required]' in option_help:
            option_help.replace('[required]', r'[arg]\[required][/]')
        
        if '[default: ' in option_help:
            option_help, _, default_value = option_help[:-1].partition('[default: ')
            option_help += fr'[hint]\[default: [secondary]{default_value}[/]][/]'

        return (option_name, option_help)

    def format_usage(self, ctx: click.Context, formatter: click.HelpFormatter) -> None:
        """
        Writes the usage line into the formatter.

        cs_tools additions:
          - adds some color to the usage text with the help of rich.
        """
        pieces = self.collect_usage_pieces(ctx)
        args = ' '.join(pieces)
        formatter.write_usage(f'[primary]{ctx.command_path}[/]', args)

    def collect_usage_pieces(self, ctx: click.Context) -> List[str]:
        """
        Returns all the pieces that go into the usage
        line and returns it as a list of strings.

        cs_tools additions:
          - adds color to usage pieces.
        """
        OPTIONS_METAVAR_IS_DEFAULT = self.options_metavar == '[OPTIONS]'

        rv = [] if OPTIONS_METAVAR_IS_DEFAULT else [f'[opt]{self.options_metavar}[/]']
        cfg  = ''
        opts = []
        args = []

        for param in self.get_params(ctx):
            if param.hidden:
                continue
            if param.name in ('help', 'helpfull'):
                continue

            if param.name == 'config' and param.param_type_name == 'option':
                default = _meta_config().get('default', {}).get('config', None)
                cfg_name = param.metavar if default is None else f'[secondary]{default}[/]'
                cfg = f'--config {cfg_name}'
                continue

            if param.param_type_name == 'argument':
                args.extend(param.get_usage_pieces(ctx))

            if param.param_type_name == 'option':
                opts.extend(param.opts)

        if args:
            rv.append(f"[arg]{' '.join(args)}[/]")

        if OPTIONS_METAVAR_IS_DEFAULT:
            if not opts:
                truncated = ['--help']
            elif len(opts) == 1:
                truncated = [opts[0], '--help']
            else:
                truncated = [opts[0], '...', '--help']
            
            joined = ', '.join(truncated)
            rv.append(fr"[opt]\[{joined}][/]")

        return [*rv, cfg]

    def format_options(self, ctx: click.Context, formatter: click.HelpFormatter) -> None:
        """
        Writes all the options into the formatter if they exist.

        cs_tools additions:
         - adds color to the options text with the help of rich.
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

            with formatter.section('[opt]Options[/]'):
                formatter.write_dl(options)

    def get_help_option(self, ctx: click.Context) -> Optional[click.Option]:
        """
        Returns the help option object.
        """
        help_options = self.get_help_option_names(ctx)

        if not help_options or not self.add_help_option:
            return None

        def show_help(ctx: click.Context, param: click.Parameter, value: str) -> None:
            if value and not ctx.resilient_parsing:
                self.show_help_and_exit(ctx)

        return click.Option(
            help_options,
            is_flag=True,
            is_eager=True,
            expose_value=False,
            callback=show_help,
            help='Show this message and exit.',
        )


class CSToolsCommand(CSToolsPrettyMixin, click.Command):
    """
    Represent a CS Tools command.
    """

    def __init__(self, **kw):
        self.dependencies = getattr(kw['callback'], 'dependencies', [])
        self._extra_params = [o for d in self.dependencies for o in (d.options or [])]
        kw['params'].extend(self._extra_params)
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

        cs_tools additions:
          - add color to the options text with the help of rich.
        """
        arguments = []

        for param in self.get_params(ctx):
            r = param.get_help_record(ctx)

            if r is not None and isinstance(param, click.Argument):
                arguments.append(r)

        if arguments:
            with formatter.section('[arg]Arguments[/]'):
                formatter.write_dl(arguments)

    # INHERITANCE OVERRIDES

    def parse_args(self, ctx: click.Context, args: List[str]) -> List[str]:
        """
        Argument parsing with extras.

        cs_tools additions:
          - guard against cli inputs which require helptext.
          - inject dependencies prior to command execution.
          - handle errors
        """
        if self.help_cmd_or_no_input(args, ctx=ctx):
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
                args_str = ' '.join(map(str, args))
                s = 's' if len(args) > 1 else ''
                ctx.fail(f'Got unexpected extra argument{s} ({args_str})')
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
        kw['subcommand_metavar'] = kw['subcommand_metavar'] or '<command>'
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

    def collect_usage_pieces(self, ctx: click.Context) -> List[str]:
        """
        Returns all the pieces that go into the usage
        line and returns it as a list of strings.

        cs_tools additions:
          - Adds color to usage pieces.
          - Add the subcommand_metavar.
        """
        rv = super().collect_usage_pieces(ctx)
        rv.insert(0, f'[arg]{self.subcommand_metavar}[/]')
        return rv

    def format_options(self, ctx: click.Context, formatter: click.HelpFormatter) -> None:
        """
        Writes all the options into the formatter if they exist.

        cs_tools additions:
          - also call .format_commands()
        """
        super().format_options(ctx, formatter)
        self.format_commands(ctx, formatter)

    def format_commands(self, ctx: click.Context, formatter: click.HelpFormatter) -> None:
        """
        Extra format methods for multi methods that adds all the
        commands after the options.

        Nearly direct copy from source:
          https://github.com/pallets/click/blob/main/src/click/core.py#L1571

        cs_tools additions:
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

                with formatter.section(f'[arg]{section}[/]'):
                    formatter.write_dl(rows)
