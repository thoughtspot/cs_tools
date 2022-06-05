import pathlib
import shutil
import os

import nox_poetry as nox


ON_GITHUB = 'GITHUB_ACTIONS' in os.environ
PY_VERSIONS = ["3.6.8", "3.7", "3.8", "3.9", "3.10"]
DIST_PKGS = pathlib.Path(__file__).parent / 'dist' / 'pkgs'


@nox.session(python="3.10", reuse_venv=not ON_GITHUB)
def vendor_packages(session):
    """
    Build offline distributable installer.
    """
    session.run("poetry", "install", external=True)
    session.run(
        "poetry", "export",
        "-f", "requirements.txt",
        "--output", (DIST_PKGS / "requirements.txt").as_posix(),
        "--without-hashes",
        external=True
    )

    _common = ('--dest', DIST_PKGS.as_posix(), '--no-cache-dir')

    session.run("pip", "download", "-r", "requirements.txt", *_common)
    session.run("pip", "download", "poetry-core", *_common)
    session.run("poetry", "build", "--format", "wheel")
    whl = pathlib.Path(next(DIST_PKGS.parent.glob('cs_tools*.whl')))
    shutil.move(whl, DIST_PKGS / whl.name)


@nox.session(python=PY_VERSIONS, reuse_venv=not ON_GITHUB)
def tests(session):
    """
    Ensure we test our code.
    """
    session.run("poetry", "install", external=True)
    session.run("ward")


# @nox.session(python=PY_VERSIONS, reuse_venv=not ON_GITHUB)
# def code_quality(session):
#     session.run("poetry", "install", external=True)
