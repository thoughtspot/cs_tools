from inspect import Signature, Parameter
import typing

from rich.console import Console
from typer import Argument as A_, Option as O_
import typer
import click

from cs_tools.helpers.loader import BSTool
from cs_tools.const import CONSOLE_THEME, PACKAGE_DIR


console = Console(theme=CONSOLE_THEME)


def show_version(show: bool):
    """
    """
    if not show:
        return

    ctx = click.get_current_context()

    for path in (PACKAGE_DIR / 'tools').iterdir():
        if path.name.endswith(ctx.command.name):
            tool = BSTool(path)
            break

    print(f'bee-boop! ({tool.version})')
    raise typer.Exit()


def show_full_help(show: bool):
    """
    """
    if not show:
        return

    ctx = click.get_current_context()

    unhidden_opts = []

    for param in ctx.command.params:
        if param.human_readable_name == 'full_help':
            continue

        param.hidden = False
        unhidden_opts.append(param)

    ctx.command.params = unhidden_opts
    console.print(ctx.get_help())
    raise typer.Exit()


def show_tool_options(
    version: bool=O_(False, '--version', help='Show the tool\'s version and exit.', show_default=False),
    helpfull: bool=O_(False, '--helpfull', help='Show the full help message and exit.', show_default=False)
):
    """
    Care for the hidden options.
    """
    ctx = click.get_current_context()

    if ctx.invoked_subcommand:
        return

    if version:
        show_version(True)

    if helpfull:
        show_full_help(True)

    console.print(ctx.get_help())
    raise typer.Exit()


def frontend(f: typing.Callable) -> typing.Callable:
    """
    Decorator that adds frontend-specific command args.
    """
    param_info = {
        'config': {
            'type': str,
            'arg': O_(None, help='config file identifier', hidden=True)
        },
        'host': {
            'type': str,
            'arg': O_(None, help='thoughtspot server', hidden=True)
        },
        'port': {
            'type': int,
            'arg': O_(None, help='optional, port of the thoughtspot server', hidden=True)
        },
        'username': {
            'type': str,
            'arg': O_(None, help='username when logging into ThoughtSpot', hidden=True)
        },
        'password': {
            'type': str,
            'arg': O_(None, help='password when logging into ThoughtSpot', hidden=True)
        },
        'disable_ssl': {
            'type': bool,
            'arg': O_(None, '--disable_ssl', help='disable SSL verification', hidden=True)
        },
        'disable_sso': {
            'type': bool,
            'arg': O_(None, '--disable_sso', help='disable automatic SAML redirect', hidden=True)
        },
        'helpfull': {
            'type': bool,
            'arg': O_(
                False, '--helpfull', help='Show the full help message and exit.',
                callback=show_full_help, is_eager=True, show_default=False
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
