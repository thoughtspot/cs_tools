from subprocess import PIPE, Popen
from typing import List
from types import ModuleType
import pkg_resources
import importlib
import logging
import pathlib
import json
import sys
import os

from cs_tools.sync.protocol import SyncerProtocol
from cs_tools.sync._compat import version


log = logging.getLogger(__name__)


class SyncerProtocolError(Exception):
    """
    Raised when a Custom Syncer breaks the contract.
    """


def is_installed(package: str) -> bool:
    """
    Determine if a package is installed or not.
    """
    try:
        pkg_resources.get_distribution(package)
        return True
    except (pkg_resources.ResolutionError, pkg_resources.ExtractionError):
        req = pkg_resources.Requirement.parse(package)

    try:
        installed_version = version(req.project_name)

        # this happens when an install fails is aborted while in progress
        if installed_version is None:
            return False

        return installed_version in req
    except ModuleNotFoundError:
        return False


def pip_install(package: str) -> None:
    """
    Programmatically install a package.

    Currently, this is a very strict implementation of the pip command
    below. It could easily be extended to accept many other pip args,
    like find-links or other.

        python -m pip install --quiet package==version
    """
    env = os.environ.copy()
    args = [sys.executable, '-m', 'pip', 'install', '--quiet', package]

    with Popen(args, stdin=PIPE, stdout=PIPE, stderr=PIPE, env=env) as proc:
        _, stderr = proc.communicate()

        if proc.returncode != 0:
            err = stderr.decode('utf-8').lstrip().strip()
            log.error(f'unable to install package: {package}: {err}')


def ensure_dependencies(requirements: List[str]) -> None:
    for requirement in requirements:
        log.debug(f'processing requirement: {requirement}')
        req = pkg_resources.Requirement.parse(requirement)

        if is_installed(req.project_name):
            log.debug('requirement satisfied, no install necessary')
            continue

        log.info(f'installing package: {requirement}')
        pip_install(requirement)


def module_from_fp(fp: pathlib.Path) -> ModuleType:
    """
    Programmatically import a module from a filepath.

    Further in-package imports from the module must use relative syntax.

        from . import foo
    """
    # __name__ = fp.stem
    __name__ = f'cs_tools_{fp.parent.stem}_syncer'
    __file__ = fp
    __path__ = [fp.parent.as_posix()]

    spec = importlib.util.spec_from_file_location(__name__, __file__, submodule_search_locations=__path__)
    module = importlib.util.module_from_spec(spec)

    # add to already-loaded modules, so further imports within each directory will work
    sys.modules[__name__] = module

    spec.loader.exec_module(module)
    return module


def load_syncer(*, protocol: str, manifest_path: pathlib.Path) -> SyncerProtocol:
    """
    """
    with manifest_path.open('r') as j:
        manifest = json.load(j)

    if 'name' not in manifest:
        manifest['name'] = manifest_path.parent.stem

    if 'requirements' not in manifest:
        manifest['requirements'] = []

    if 'syncer_class' not in manifest:
        raise SyncerProtocolError(f'{protocol} manifest is missing a top-level directive for "syncer_class"')

    log.debug(f'manifest digest:\n\n{manifest}\n')
    ensure_dependencies(manifest['requirements'])

    mod = module_from_fp(manifest_path.parent / 'syncer.py')
    cls = getattr(mod, manifest['syncer_class'])

    if not hasattr(cls, 'name'):
        raise SyncerProtocolError(f'{protocol} syncer must define an attribute for "name"')

    if not hasattr(cls, 'load'):
        raise SyncerProtocolError(f'{protocol} syncer does not define the "load" method')

    if not hasattr(cls, 'dump'):
        raise SyncerProtocolError(f'{protocol} syncer does not define the "dump" method')

    return cls
