from __future__ import annotations

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
from cs_tools.sync import base
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
    no_args_is_help=True,
    invoke_without_command=True,
)


@app.command(cls=CSToolsCommand)
def sync():
    """
    Sync your local environment with the most up-to-date dependencies.
    """
    # RIGHT NOW, we limit to these packages only.
    # - thoughtspot_tml
    #
    cs_tools_venv.pip("install", "thoughtspot_tml", "--upgrade", "--upgrade-strategy", "eager")


@app.command(cls=CSToolsCommand, name="update")
@app.command(cls=CSToolsCommand, name="upgrade", hidden=True)
def update(
    beta: bool = typer.Option(False, "--beta", help="pin your install to a pre-release build"),
    dev: pathlib.Path = typer.Option(None, help="pin your install to a local build", click_type=Directory()),
    offline: pathlib.Path = typer.Option(
        None, help="install cs_tools from a local directory instead of from github", click_type=Directory()
    ),
):
    """
    Upgrade CS Tools.
    """
    log.info("Determining if CS Tools is globally installed.")
    cs_tools_venv.check_if_globally_installed(remove=True)

    if offline is not None:
        log.info(f"Using the offline binary found at [b magenta]{offline}")
        cs_tools_venv.with_offline_mode(find_links=offline)
        requires = ["cs_tools[cli]"]

    elif dev is not None:
        log.info("Installing locally using the development environment.")
        requires = [f"cs_tools[cli] -e {dev.as_posix()}"]

    else:
        log.info(f"Getting the latest CS Tools {'beta ' if beta else ''}release.")
        release = get_latest_cs_tools_release(allow_beta=beta)
        log.info(f"Found version: [b cyan]{release['tag_name']}")
        requires = [f"cs_tools[cli] @ https://github.com/thoughtspot/cs_tools/archive/{release['tag_name']}.zip"]

        if AwesomeVersion(release["tag_name"]) <= AwesomeVersion(__version__):
            log.info(f"CS Tools is [b green]already up to date[/]! (your version: {__version__})")
            raise typer.Exit(0)

    log.info("Upgrading CS Tools and its dependencies.")
    cs_tools_venv.pip("install", *requires, "--upgrade", "--upgrade-strategy", "eager", raise_on_failure=False)


@app.command(cls=CSToolsCommand)
def info(
    directory: pathlib.Path = typer.Option(
        None, help="export an image to share with the CS Tools team", click_type=Directory()
    ),
    anonymous: bool = typer.Option(False, "--anonymous", help="remove personal references from the output"),
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
        f"\n System Python Path: [b yellow]{cs_tools_venv.system_exe}[/]"
        f"\n      Platform Tags: [b yellow]{sysconfig.get_platform()}[/]"
        f"\n"
    )

    if anonymous:
        text = utils.anonymize(text, anonymizer=" [dim]{anonymous}[/] ")

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
    directory: pathlib.Path = typer.Option(help="location to download the python binaries to", click_type=Directory()),
    platform: str = typer.Option(help="tag describing the OS and CPU architecture of the target environment"),
    python_version: AwesomeVersion = typer.Option(
        metavar="X.Y", help="major and minor version of your python install", parser=AwesomeVersion
    ),
    beta: bool = typer.Option(False, "--beta", help="if included, download the latest pre-release binary"),
    syncer_dialect: str = typer.Option(None, "--syncer", help="the name of the dialect to fetch dependencies for"),
):
    """
    Generate an offline binary.

    Customers without outside access to the internet will need to install from a local
    directory instead. This commanad will download the necessary files in order to do
    so. Have the customer execute the below command so you have the necessary
    information to generate this binary.

       [b yellow]python -m sysconfig[/]

    """
    # DEV NOTE: @boonhapus, 2024/05/21
    #
    # The idea behind the offline installer is to simulate `pip install` by downloading
    # all the necessary packages to build our environment.
    #
    dir_to_zip = directory.joinpath("TEMPORARY__DO_NOT_TOUCH")
    # ZIPFILE STRUCTURE
    # |- requirements.txt
    # |  dependencies/
    #    |- abc.whl
    #    |- ...
    #
    dir_to_zip.joinpath("dependencies").mkdir(exist_ok=True, parents=True)
    dir_to_zip.joinpath("requirements.txt").write_text("cs_tools[cli]\n")

    log.info("Fetching latest CS Tools release from GitHub")
    release_info = get_latest_cs_tools_release(allow_beta=beta)
    release_tag = release_info["tag_name"]

    if syncer_dialect is not None:
        syncer_dir = utils.get_package_directory("cs_tools") / "sync" / syncer_dialect

        if not syncer_dir.exists():
            log.error(f"Syncer dialect {syncer_dialect} not found")
            raise typer.Exit(1)

        log.info(f"Fetching {syncer_dialect} syncer dependencies")
        manifest = base.SyncerManifest.model_validate_json(syncer_dir.joinpath("MANIFEST.json").read_text())
        manifest.__ensure_pip_requirements__()

        with dir_to_zip.joinpath("requirements.txt").open(mode="a") as r:
            for requirement in manifest.requirements:
                r.write(f"{requirement}\n")

    # freeze our own environment, which has all the dependencies needed to build
    log.info("Freezing existing virtual environment")
    frozen = {
        r
        for r in cs_tools_venv.pip("freeze", "--quiet", should_stream_output=False).stdout.decode().split("\n")
        if "cs_tools" not in r
    }

    # add in the latest release
    frozen.add(f"cs_tools @ https://github.com/thoughtspot/cs_tools/archive/{release_tag}.zip")

    # DESIRED OUTPUT
    #
    # Running command /usr/bin/python /tmp/pip-standalone-pip-ccumgmp2/__env_pip__.zip/pip install --ignore-installed --no-user --prefix /tmp/pip-build-env-dtapuowm/overlay --no-warn-script-location --no-binary :none: --only-binary :none: -i https://pypi.org/simple -- 'setuptools>=42' 'setuptools_scm[toml]>=6.2'
    #

    # add packaging stuff since we'll use --no-deps
    frozen.add("pip >= 23.1")
    frozen.add("setuptools >= 42")
    frozen.add("setuptools_scm >= 6.2")
    frozen.add("wheel")
    # rust-based build tools
    frozen.add("semantic-version >= 2.10.0")
    frozen.add("setuptools-rust >= 1.4.0")
    frozen.add("maturin >= 1, < 2")

    # fmt: off
    # add in version specific constraints (in case they don't get exported from the current environment)
    if python_version < "3.11.0":
        frozen.add("strenum >= 0.4.9")            # from cs_tools
        frozen.add("tomli >= 1.1.0")              # from ...

    if "win" in platform:
        frozen.add("pyreadline3 == 3.4.1")        # from cs_tools

    log.info("Downloading dependent packages")
    cs_tools_venv.pip(
        "download", *frozen,
        "--no-deps",  # we shouldn't need transitive dependencies, since we've build all the dependencies above
        "--dest", dir_to_zip.joinpath("dependencies").as_posix(),
        "--implementation", "cp",
        "--python-version", f"{python_version.major}{python_version.minor}",
        "--platform", platform.replace("-", "_"),
    )
    # fmt: on

    # rename the cs_tools .zip files to their actual package names
    dir_to_zip.joinpath(f"dependencies/{release_tag}.zip").rename(dir_to_zip / f"dependencies/cs_tools-{release_tag[1:]}.zip")  # noqa: E501

    from cs_tools.updater import _bootstrapper, _updater

    zip_fp = directory.joinpath(f"cs-tools_{__version__}_{platform}_{python_version}")

    log.info(f"Preparing your download at {zip_fp}")
    shutil.copy(_bootstrapper.__file__, dir_to_zip.joinpath("_bootstrapper.py"))
    shutil.copy(_updater.__file__, dir_to_zip.joinpath("_updater.py"))
    shutil.make_archive(zip_fp.as_posix(), "zip", dir_to_zip)
    shutil.rmtree(dir_to_zip)
