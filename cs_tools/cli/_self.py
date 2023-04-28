import sysconfig
import platform
import logging
import pathlib
import sys
import os

from awesomeversion import AwesomeVersion
from rich.panel import Panel
import typer

from cs_tools.updater._bootstrapper import get_latest_cs_tools_release
from cs_tools._version import __version__
from cs_tools.settings import _meta_config as meta
from cs_tools.updater import CSToolsVirtualEnvironment
from cs_tools.updater import FishPath, WindowsPath, UnixPath
from cs_tools.cli.ux import CSToolsOption as Opt
from cs_tools.cli.ux import CSToolsCommand
from cs_tools.cli.ux import CSToolsGroup
from cs_tools.cli.ux import rich_console
from cs_tools.const import APP_DIR
from cs_tools.cli import _analytics

log = logging.getLogger(__name__)
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


@app.command(cls=CSToolsCommand, name="upgrade", hidden=True)
@app.command(cls=CSToolsCommand)
def update(
    beta: bool = Opt(False, "--beta", help="pin your install to a pre-release build"),
    offline: pathlib.Path = Opt(
        None,
        help="install cs_tools from a distributable directory instead of from github",
        file_okay=False,
        resolve_path=True,
    ),
    venv_name: str = Opt(None, "--venv-name", hidden=True),
):
    """
    Upgrade CS Tools.
    """
    if venv_name is not None:
        os.environ["CS_TOOLS_CONFIG_DIRNAME"] = venv_name

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
    venv = CSToolsVirtualEnvironment(find_links=offline)

    try:
        rc = venv.pip("install", requires, "--upgrade")
        log.debug(rc)
    except RuntimeError:  # OSError when pip on Windows can't upgrade itself~
        pass


    try:
        syncer = _analytics.get_database()
        syncer.dump("runtime_environment", data=[_analytics.RuntimeEnvironment(envt_uuid=meta.install_uuid).dict()])
    except sa.exc.OperationalError:
        pass

    # Would you like to send Analytics to CS Tools?


@app.command(cls=CSToolsCommand)
def info():
    """
    Get information on your install.
    """
    if platform.system() == "Windows":
        source = pathlib.Path(sys.executable).parent.joinpath("Activate.ps1")
    else:
        source = f"source {pathlib.Path(sys.executable).parent.joinpath('activate')}"

    rich_console.print(
        Panel.fit(
            f"\n           CS Tools: [b yellow]{__version__}[/]"
            f"\n     Python Version: [b yellow]Python {sys.version}[/]"
            f"\n        System Info: [b yellow]{platform.system()}[/] (detail: [b yellow]{platform.platform()}[/])"
            f"\n  Configs Directory: [b yellow]{APP_DIR}[/]"
            f"\nActivate VirtualEnv: [b yellow]{source}[/]"
            f"\n      Platform Tags: [b yellow]{sysconfig.get_platform()}[/]"
            f"\n",
            padding=(0, 4, 0, 4)
        )
    )


@app.command(cls=CSToolsCommand, hidden=True)
def pip():
    """
    Remove CS Tools.
    """
    # if venv_name is not None:
    #     os.environ["CS_TOOLS_CONFIG_DIRNAME"] = venv_name

    # venv = CSToolsVirtualEnvironment()
    # venv.pip()
    raise NotImplementedError("Not yet.")


@app.command(cls=CSToolsCommand, hidden=True)
def download(
    directory: pathlib.Path = Opt(..., help="location to download the python binaries to"),
    platform: str = Opt(..., help="tag which describes the OS and CPU architecture of the target environment"),
    python_version: AwesomeVersion = Opt(
        ...,
        metavar="X.Y",
        help="major and minor version of your python install",
        custom_type=AwesomeVersion,
    ),
    beta: bool = Opt(False, "--beta", help="if included, download the latest pre-release binary"),
):
    """
    Generate an offline binary.

    Customers without outside access to the internet will need to install from a local
    directory instead. This commanad will download the necessary files in order to do
    so. Have the customer execute the below command so you have the necessary
    information to generate this binary.

       [b blue]python -m sysconfig[/]

    """
    release_info = get_latest_cs_tools_release(allow_beta=beta)
    release_tag = release_info["tag_name"]

    venv = CSToolsVirtualEnvironment()

    # freeze our own environment, which has all the dependencies needed to build
    frozen = {req for req in venv.pip("freeze", "--quiet") if "cs_tools" not in req}

    # add packaging stuff since we'll see --no-index
    frozen.update(("setuptools", "wheel"))

    # add in version specific constraints (in case they don't get exported from the current environment)
    if python_version < "3.11.0":
        frozen.add("strenum >= 0.4.9")            # from cs_tools
        frozen.add("tomli >= 1.1.0")              # from ...

    if python_version < "3.10.0":
        frozen.add("zipp >= 3.11.0")              # from horde

    if python_version < "3.8.0":
        frozen.add("typing_extensions >= 4.4.0")  # from cs_tools

    if "win" in platform:
        frozen.add("pyreadline3 == 3.4.1")        # from cs_tools

    # add in the latest release
    frozen.add(f"cs_tools @ https://github.com/thoughtspot/cs_tools/archive/{release_tag}.zip")

    venv.pip(
        "download", *frozen,
        "--no-deps",  # we've build all the dependencies above
        "--dest", directory.as_posix(),
        "--implementation", "cp",
        "--python-version", f"{python_version.major}{python_version.minor}",
        "--platform", platform.replace("-", "_"),
    )

    # rename .zip files we author to their actual package names
    directory.joinpath("dev.zip").rename(directory / "horde-1.0.0.zip")
    directory.joinpath(f"{release_tag}.zip").rename(directory / f"cs_tools-{release_tag[1:]}.zip")


@app.command(cls=CSToolsCommand, hidden=True)
def uninstall(
    delete_configs: bool = Opt(False, "--delete-configs", help="delete all the configurations in CS Tools directory")
):
    """
    Remove CS Tools.
    """
    raise NotImplementedError("Not yet.")
