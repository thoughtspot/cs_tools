from __future__ import annotations

import contextlib
import datetime as dt
import logging
import pathlib
import shutil
import sys
import zipfile

from cs_tools import __version__, _types, updater, utils
from cs_tools.cli import custom_types
from cs_tools.cli.ux import RICH_CONSOLE, AsyncTyper
from cs_tools.settings import _meta_config as meta
from cs_tools.sync import base
from cs_tools.updater._bootstrapper import get_latest_cs_tools_release
from cs_tools.updater._updater import cs_tools_venv
import rich
import typer

_LOG = logging.getLogger(__name__)
app = AsyncTyper(
    name="self",
    help=f"""
    Perform actions on CS Tools.

    {meta.newer_version_string()}
    """,
)


@app.command()
def info(
    directory: pathlib.Path = typer.Option(
        None,
        help="Where to export the info to share with the CS Tools team.",
        click_type=custom_types.Directory(exists=False, make=True),
    ),
    anonymous: bool = typer.Option(False, "--anonymous", help="remove personal references from the output"),
) -> _types.ExitCode:
    """Get information on your install."""
    if meta.local_system.is_windows:
        source = f"{pathlib.Path(sys.executable).parent.joinpath('Activate.ps1')}"
    else:
        source = f'source "{pathlib.Path(sys.executable).parent.joinpath("activate")}"'

    text = (
        f"\n       [fg-secondary]Info snapshot[/] taken on [fg-success]{dt.datetime.now(tz=dt.timezone.utc).date()}[/]"
        f"\n"
        f"\n           CS Tools: [fg-warn]{__version__}[/]"
        f"\n     Python Version: [fg-warn]Python {sys.version}[/]"
        f"\n        System Info: [fg-warn]{meta.local_system.system}[/]"
        f"\n  Configs Directory: [fg-warn]{cs_tools_venv.base_dir}[/]"
        f"\nActivate VirtualEnv: [fg-warn]{source}[/]"
        f"\n      Platform Tags: [fg-warn]{utils.platform_tag()}[/]"
        f"\n"
    )
    if anonymous:
        text = utils.anonymize(text, anonymizer=" [dim]{anonymous}[/] ")

    renderable = rich.align.Align.center(rich.panel.Panel.fit(text, padding=(0, 4, 0, 4)))

    @contextlib.contextmanager
    def noop():
        """Do nothing."""
        yield

    screenshotter = (
        noop()
        if directory is None
        else utils.record_screenshots(
            RICH_CONSOLE,
            path=directory / f"cs-tools-info-{dt.datetime.now(tz=dt.timezone.utc):%Y-%m-%d}.svg",
            title="cs_tools self info",
        )
    )

    with screenshotter:
        RICH_CONSOLE.print(renderable)

    return 0


@app.command()
def sync() -> _types.ExitCode:
    """Sync your local environment with the most up-to-date dependencies."""
    # CURRENTLY, THIS ONLY AFFECTS..
    # - thoughtspot_tml ..... WHICH CAN OFTEN CHANGE BETWEEN CS TOOL RELEASES
    # - tzdata (WIN only) ... WHICH UPDATES USUALLY EVERY YEAR
    PACKAGES_TO_SYNC = ["thoughtspot_tml"]

    if meta.local_system.is_windows:
        PACKAGES_TO_SYNC.append("tzdata")

    for package in PACKAGES_TO_SYNC:
        cs_tools_venv.install(package, "--upgrade", "--prerelease=allow")

    return 0


@app.command(name="upgrade", hidden=True)
@app.command(name="update")
def update(
    beta: custom_types.Version = typer.Option(None, "--beta", help="The specific beta version to fetch from Github."),
    offline: custom_types.Directory = typer.Option(None, help="Install cs_tools from a local directory."),
) -> _types.ExitCode:
    """Upgrade CS Tools."""
    assert isinstance(offline, pathlib.Path), "offline directory must be a pathlib.Path"

    if offline is not None:
        cs_tools_venv.offline_index = offline
        where = offline.as_posix()
    else:
        # FETCH THE VERSION TO INSTALL.
        ref = beta if beta is not None else get_latest_cs_tools_release().get("tag_name", f"v{__version__}")
        where = f"https://github.com/thoughtspot/cs_tools/archive/{ref}.zip"

    cs_tools_venv.install(f"cs_tools[cli] @ {where}", raise_if_stderr=False)
    return 0


@app.command(name="export", hidden=True)
@app.command(name="download")
def _make_offline_distributable(
    directory: pathlib.Path = typer.Option(
        ...,
        help="Location to export the python distributable to.",
        click_type=custom_types.Directory(exists=False, make=True),
    ),
    platform: str = typer.Option(help="A tag describing the target environment architecture, see --help for details."),
    python_version: custom_types.Version = typer.Option(
        metavar="X.Y", help="The major and minor version of the target Python environment, see --help for details"
    ),
    beta: str = typer.Option(None, metavar="X.Y.Z", help="The specific beta version to fetch from Github."),
    syncer: str = typer.Option(None, metavar="DIALECT", help="Name of the dialect to fetch dependencies for."),
) -> _types.ExitCode:
    """
    Create an offline distribution of this CS Tools environment.

    \b
    Q. How can I find my platform?
    >>> [fg-secondary]python -c "from pip._vendor.packaging.tags import platform_tags; print(next(iter(platform_tags())))"[/]

    Q. How can I find my python version?
    >>> [fg-secondary]python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')"[/]

    Q. Do I need anything other than python?
    A. You also likely need a rust compiler, which can be installed via Rust ( https://www.rust-lang.org/tools/install ).
    """
    assert isinstance(directory, pathlib.Path), "directory must be a pathlib.Path"

    # ENSURE WE HAVE THE DESIRED SYNCER INSTALLED.
    if syncer is not None:
        syncer_base_dir = utils.get_package_directory("cs_tools") / "sync" / syncer.lower()
        assert syncer_base_dir.exists(), f"Syncer dialect '{syncer}' not found, did you mistype it?"
        syncer_manifest = base.SyncerManifest.model_validate_json(syncer_base_dir.joinpath("MANIFEST.json").read_text())

        for requirement_info in syncer_manifest.requirements:
            cs_tools_venv.install(str(requirement_info.requirement), *requirement_info.pip_args)

    # FETCH THE VERSION TO INSTALL.
    ref = beta if beta is not None else get_latest_cs_tools_release().get("tag_name", f"v{__version__}")

    try:
        # fmt: off
        cs_tools_venv.run(
            cs_tools_venv.python.as_posix(), "-m", "pip", "download",
            f"cs_tools[cli] @ https://github.com/thoughtspot/cs_tools/archive/{ref}.zip",
            "--dest", directory.as_posix(),
            raise_if_stderr=True,
        )
        # fmt: on
    except RuntimeError:
        _LOG.error(f"Failed to fetch requirements for CS Tools version [fg-error]{ref}, see logs for details..")
        return 1

    # CREATE A ZIP / WHEEL OF OURSELVES.
    next(directory.glob(f"{ref}*.zip")).rename(directory / f"cs_tools-{ref}.zip")

    # GENERATE THE DIRECTORY OF DEPENDENCIES.
    cs_tools_venv.make_offline_distribution(output_dir=directory, platform=platform, python_version=python_version)

    # COPY THE BOOTSTRAPPER AND UPDATER SCRIPTS
    shutil.copyfile(updater._updater.__file__, directory / "_updater.py")
    shutil.copyfile(updater._bootstrapper.__file__, directory / "_bootstrapper.py")

    # ZIP IT UP
    zipfile_name = directory / f"cs-tools-{__version__}-{platform}-{python_version}.zip"
    _LOG.info(f"Zipping CS Tools venv > {zipfile_name}")
    utils.make_zip_archive(directory=directory, zipfile_path=zipfile_name, compression=zipfile.ZIP_DEFLATED)

    # DELETE THE EXTRA FILES.
    for path in directory.iterdir():
        if path == zipfile_name:
            continue

        if path.is_dir():
            shutil.rmtree(path, ignore_errors=True)

        if path.is_file():
            path.unlink(missing_ok=True)

    # PRINT A NOTE ON HOW TO INSTALL.
    RICH_CONSOLE.print(
        f"""
        [fg-warn]INSTALL INSTRUCTIONS[/]
        1. Extract the zip file.
        2. Move into the directory with all the python dependencies.
        3. Run [fg-secondary]python[/] against the _bootstrapper.py file with [fg-secondary]--offline-mode[/] specified

        [fg-warn]cd[/] [fg-secondary]{zipfile_name.stem}[/]
        [fg-warn]python[/] [fg-secondary]_bootstrapper.py --install --offline-mode --no-clean[/]
        """
    )

    return 0
