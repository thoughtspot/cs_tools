import subprocess as sp
import os

from typer import Argument as A_, Option as O_
import typer

from cs_tools.cli.ux import console, CSToolsGroup, CSToolsCommand
from cs_tools.const import PACKAGE_DIR


app = typer.Typer(
    cls=CSToolsGroup,
    name="cs_scripts",
    help="""
    Welcome to CS Scripts!

    [bold yellow]You must have a development install in order to run these commands![/]
    """,
    add_completion=False,
    context_settings={
        # global settings
        'help_option_names': ['--help', '-h', '--helpfull'],

        # allow responsive console design
        'max_content_width':
            console.width if console.width <= 120 else max(120, console.width * .65),

        # allow case-insensitive commands
        'token_normalize_func': lambda x: x.lower()
    },
    options_metavar='[--version, --help]'
)


@app.command(cls=CSToolsCommand)
def develop_docs():
    """
    """
    sp.check_output(['mkdocs', 'serve'])


@app.command(cls=CSToolsCommand)
def run_tests(cfg_name: str = O_(..., help='which configuration file to use')):
    """
    """
    os.environ['WARD_TS_CONFIG_NAME'] = cfg_name
    cmd =  'coverage run -m ward'
    # cmd += ' && coverage report -m'

    with sp.Popen(cmd, stdout=sp.PIPE, cwd=PACKAGE_DIR.parent) as proc:
        for line in proc.stdout:
            console.log(line.decode().strip())


@app.command()
def vendor_pkgs():
    """
    """
    sp.check_output(['nox', '--sessions', 'ensure_working_local_install'])


if __name__ == '__main__':
    app()
