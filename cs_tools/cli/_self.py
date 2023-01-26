import logging
import pathlib

from awesomeversion import AwesomeVersion
import typer

from cs_tools.updater._bootstrapper import get_latest_cs_tools_release
from cs_tools._version import __version__
from cs_tools.settings import _meta_config
from cs_tools.updater import CSToolsVirtualEnvironment
from cs_tools.updater import FishPath, WindowsPath, UnixPath
from cs_tools.cli.ux import CSToolsOption as Opt
from cs_tools.cli.ux import CSToolsCommand
from cs_tools.cli.ux import CSToolsGroup
from cs_tools.cli.ux import rich_console

log = logging.getLogger(__name__)
meta = _meta_config()
app = typer.Typer(
    cls=CSToolsGroup,
    name="self",
    help=f"""
    Perform actions on CS Tools.

    {meta.newer_version_string()}
    """,
    invoke_without_command=True,
    no_args_is_help=True,
)


@app.command(cls=CSToolsCommand)
def upgrade(
    beta: bool = Opt(False, "--beta", help="pin your install to a pre-release build"),
    offline: pathlib.Path = Opt(
        None,
        help="install cs_tools from a distributable directory instead of from remote",

    ),
):
    """
    Upgrade CS Tools.
    """
    import os
    os.environ["CS_TOOLS_CONFIG_DIRNAME"] = "cs_tools_new"
    venv = CSToolsVirtualEnvironment()
    release = get_latest_cs_tools_release()
    requires = "cs_tools[cli]"

    if offline:
        log.info(f"Using the offline binary found at [b magenta]{offline}")
    else:
        log.info(f"Getting the latest CS Tools {'beta ' if beta else ''}release.")
        release = get_latest_cs_tools_release(allow_beta=beta)
        log.info(f"Found version: [b cyan]{release['tag_name']}")
        requires += f" @ https://github.com/thoughtspot/cs_tools/archive/{release['tag_name']}.zip"

        if AwesomeVersion(release["tag_name"]) <= AwesomeVersion(__version__):
            log.info("CS Tools is [b green]already up to date[/]!")
            raise typer.Exit(0)

    log.info("Upgrading CS Tools and its dependencies.")
    rc = venv.pip("install", requires)
    log.info(rc)


@app.command(cls=CSToolsCommand)
def uninstall(
    delete_configs: bool = Opt(False, "--delete-configs", help="delete all the configurations in CS Tools directory")
):
    """
    Remove CS Tools.
    """
    raise NotImplementedError("Not yet.")
