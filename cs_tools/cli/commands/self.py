from __future__ import annotations

from typing import Annotated, Optional
import datetime as dt
import logging
import pathlib
import platform
import shutil
import sys
import sysconfig

from awesomeversion import AwesomeVersion
from cs_tools import __version__, utils
from cs_tools.cli import _analytics
from cs_tools.cli.types import Directory
from cs_tools.cli.ux import CSToolsCommand, CSToolsGroup, rich_console
from cs_tools.settings import _meta_config as meta
from cs_tools.updater import cs_tools_venv
from cs_tools.updater._bootstrapper import get_latest_cs_tools_release
import rich
import typer

log = logging.getLogger(__name__)
app = typer.Typer(
    cls=CSToolsGroup,
    name="self",
    help=f"""
    Perform actions on CS Tools.

    {meta.newer_version_string()}
    """,
    invoke_without_command=True,
)


@app.command(cls=CSToolsCommand)
def sync():
    """
    Sync your local environment with the most up-to-date dependencies.
    """
    cs_tools_venv.pip("install", "--upgrade", "--upgrade-strategy", "eager")


@app.command(cls=CSToolsCommand, name="update")
@app.command(cls=CSToolsCommand, name="upgrade", hidden=True)
def update(
    beta: Annotated[bool, typer.Option("--beta", help="pin your install to a pre-release build")] = False,
    dev: Annotated[
        Optional[Directory], typer.Option(help="pin your install to a local build", click_type=Directory())
    ] = None,
    offline: Annotated[
        Optional[Directory],
        typer.Option(help="install cs_tools from a local directory instead of from github", click_type=Directory()),
    ] = None,
):
    """
    Upgrade CS Tools.
    """
    requires = "cs_tools[cli]"

    if offline is not None:
        log.info(f"Using the offline binary found at [b magenta]{offline}")
        cs_tools_venv.with_offline_mode(find_links=offline)

    elif dev is not None:
        log.info("Installing locally using the development environment.")
        requires = f"{dev.as_posix()}[cli]"

    else:
        log.info(f"Getting the latest CS Tools {'beta ' if beta else ''}release.")
        release = get_latest_cs_tools_release(allow_beta=beta)
        log.info(f"Found version: [b cyan]{release['tag_name']}")
        requires += f" @ https://github.com/thoughtspot/cs_tools/archive/{release['tag_name']}.zip"

        if AwesomeVersion(release["tag_name"]) <= AwesomeVersion(__version__):
            log.info(f"CS Tools is [b green]already up to date[/]! (your version: {__version__})")
            raise typer.Exit(0)

    log.info("Upgrading CS Tools and its dependencies.")
    cs_tools_venv.pip("install", requires, "--upgrade", "--upgrade-strategy", "eager")


@app.command(cls=CSToolsCommand)
def info(
    directory: Annotated[
        Optional[Directory],
        typer.Option(help="export an image to share with the CS Tools team", click_type=Directory()),
    ] = None,
    anonymous: Annotated[bool, typer.Option("--anonymous", help="remove personal references from the output")] = False,
):
    """
    Get information on your install.
    """
    if platform.system() == "Windows":
        source = f"{pathlib.Path(sys.executable).parent.joinpath('Activate.ps1')}"
    else:
        source = f"source \"{pathlib.Path(sys.executable).parent.joinpath('activate')}\""

    text = (
        f"\n       [b blue]Info snapshot[/] taken on [b green]{dt.datetime.now(tz=dt.timezone.utc).date()}[/]"
        f"\n"
        f"\n           CS Tools: [b yellow]{__version__}[/]"
        f"\n     Python Version: [b yellow]Python {sys.version}[/]"
        f"\n        System Info: [b yellow]{platform.system()}[/] (detail: [b yellow]{platform.platform()}[/])"
        f"\n  Configs Directory: [b yellow]{cs_tools_venv.app_dir}[/]"
        f"\nActivate VirtualEnv: [b yellow]{source}[/]"
        f"\n      Platform Tags: [b yellow]{sysconfig.get_platform()}[/]"
        f"\n"
    )

    if anonymous:
        text = utils.anonymize(text)

    renderable = rich.panel.Panel.fit(text, padding=(0, 4, 0, 4))
    rich_console.print(renderable)

    if directory is not None:
        utils.svg_screenshot(
            renderable,
            path=directory / f"cs-tools-info-{dt.datetime.now(tz=dt.timezone.utc):%Y-%m-%d}.svg",
            console=rich_console,
            centered=True,
            width="fit",
            title="cs_tools self info",
        )


@app.command(cls=CSToolsCommand, hidden=True)
def analytics():
    """Re-prompt for analytics."""
    # RESET THE ASKS
    assert meta.analytics is not None
    meta.analytics.is_opted_in = None
    meta.analytics.can_record_url = None

    _analytics.prompt_for_opt_in()
    _analytics.maybe_send_analytics_data()


@app.command(cls=CSToolsCommand, hidden=True)
def download(
    directory: Annotated[
        Directory, typer.Option(help="location to download the python binaries to", click_type=Directory())
    ],
    platform: Annotated[str, typer.Option(help="tag describing the OS and CPU architecture of the target environment")],
    python_version: Annotated[
        AwesomeVersion,
        typer.Option(metavar="X.Y", help="major and minor version of your python install", parser=AwesomeVersion),
    ],
    beta: Annotated[bool, typer.Option("--beta", help="if included, download the latest pre-release binary")] = False,
):
    """
    Generate an offline binary.

    Customers without outside access to the internet will need to install from a local
    directory instead. This commanad will download the necessary files in order to do
    so. Have the customer execute the below command so you have the necessary
    information to generate this binary.

       [b yellow]python -m sysconfig[/]

    """
    requirements = directory.joinpath("requirements")
    release_info = get_latest_cs_tools_release(allow_beta=beta)
    release_tag = release_info["tag_name"]

    venv = cs_tools_venv

    # freeze our own environment, which has all the dependencies needed to build
    frozen = {req for req in venv.pip("freeze", "--quiet").stdout.decode().split("\n") if "cs_tools" not in req}

    # add in the latest release
    frozen.add(f"cs_tools @ https://github.com/thoughtspot/cs_tools/archive/{release_tag}.zip")

    # add packaging stuff since we'll use --no-deps
    frozen.add("pip >= 23.1")
    frozen.add("setuptools >= 42")
    frozen.add("setuptools_scm >= 6.2")
    frozen.add("wheel")

    # fmt: off
    # add in version specific constraints (in case they don't get exported from the current environment)
    if python_version < "3.11.0":
        frozen.add("strenum >= 0.4.9")            # from cs_tools
        frozen.add("tomli >= 1.1.0")              # from ...

    if "win" in platform:
        frozen.add("pyreadline3 == 3.4.1")        # from cs_tools

    venv.pip(
        "download", *frozen,
        "--no-deps",  # we shouldn't need transitive dependencies, since we've build all the dependencies above
        "--dest", requirements.as_posix(),
        "--implementation", "cp",
        "--python-version", f"{python_version.major}{python_version.minor}",
        "--platform", platform.replace("-", "_"),
    )
    # fmt: on

    # rename .zip files we author to their actual package names
    requirements.joinpath(f"{release_tag}.zip").rename(requirements / f"cs_tools-{release_tag[1:]}.zip")

    from cs_tools.updater import _bootstrapper, _updater

    zip_fp = directory.joinpath(f"cs-tools_{__version__}_{platform}_{python_version}")
    shutil.copy(_bootstrapper.__file__, requirements.joinpath("_bootstrapper.py"))
    shutil.copy(_updater.__file__, requirements.joinpath("_updater.py"))
    shutil.make_archive(zip_fp.as_posix(), "zip", requirements)
    shutil.rmtree(requirements)
