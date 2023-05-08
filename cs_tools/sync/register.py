from typing import List
from types import ModuleType
import itertools as it
import importlib
import pathlib
import logging
import json
import sys

import pkg_resources

from cs_tools.updater._updater import CSToolsVirtualEnvironment
from cs_tools.sync.protocol import SyncerProtocol
from cs_tools.sync._compat import version
from cs_tools.errors import SyncerProtocolError

log = logging.getLogger(__name__)


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


def ensure_dependencies(requirements: List[str], pip_args: List[str]) -> None:
    venv = CSToolsVirtualEnvironment()

    for requirement, args in it.zip_longest(requirements, pip_args, fillvalue=[]):
        log.debug(f"processing requirement: {requirement}")
        req = pkg_resources.Requirement.parse(requirement)

        if is_installed(req.project_name):
            log.debug("requirement satisfied, no install necessary")
            continue

        log.info(f"installing package: {requirement}")
        venv.pip("install", requirement, *args)


def module_from_fp(fp: pathlib.Path) -> ModuleType:
    """
    Programmatically import a module from a filepath.

    Further in-package imports from the module must use relative syntax.

        from . import foo
    """
    __name__ = f"cs_tools_{fp.parent.stem}_syncer"
    __file__ = fp
    __path__ = [fp.parent.as_posix()]

    spec = importlib.util.spec_from_file_location(__name__, __file__, submodule_search_locations=__path__)
    module = importlib.util.module_from_spec(spec)

    # add to already-loaded modules, so further imports within each directory will work
    sys.modules[__name__] = module

    spec.loader.exec_module(module)
    return module


def load_syncer(*, protocol: str, manifest_path: pathlib.Path) -> SyncerProtocol:
    """ """
    with manifest_path.open("r") as j:
        manifest = json.load(j)

    if "name" not in manifest:
        manifest["name"] = manifest_path.parent.stem

    if "requirements" not in manifest:
        manifest["requirements"] = []

    if "syncer_class" not in manifest:
        raise SyncerProtocolError(
            protocol,
            manifest_path=manifest_path,
            reason=("manifest [blue]{manifest_path}[/] is missing a top-level directive " "for [blue]syncer_class[/]"),
        )

    log.debug(f"manifest digest:\n\n{manifest}\n")
    ensure_dependencies(manifest["requirements"], manifest.get("pip_args", []))

    mod = module_from_fp(manifest_path.parent / "syncer.py")
    cls = getattr(mod, manifest["syncer_class"])

    if not hasattr(cls, "name"):
        raise SyncerProtocolError(
            protocol,
            manifest_path=manifest_path,
            reason=("[blue]{manifest_path.parent}/syncer.py[/] must define an attribute " "for [blue]name[/]"),
        )

    if not hasattr(cls, "load"):
        raise SyncerProtocolError(
            protocol,
            manifest_path=manifest_path,
            reason=("[blue]{manifest_path.parent}/syncer.py[/] must define the " "[blue]load[/] method"),
        )

    if not hasattr(cls, "dump"):
        raise SyncerProtocolError(
            protocol,
            manifest_path=manifest_path,
            reason=("[blue]{manifest_path.parent}/syncer.py[/] must define the " "[blue]dump[/] method"),
        )

    return cls
