from __future__ import annotations

from typing import Any
import logging
import pathlib

import click
import pydantic
import sqlmodel
import toml

from cs_tools import errors, utils
from cs_tools.cli.dependencies.base import Dependency
from cs_tools.sync import base

log = logging.getLogger(__name__)


class DSyncer(Dependency):
    protocol: str
    definition_fp: pathlib.Path = None
    definition_kw: dict[str, Any] = None
    models: list[type[sqlmodel.SQLModel]] = None

    _syncer: base.Syncer = pydantic.PrivateAttr(default="NOT YET PARSED")

    @property
    def metadata(self) -> sqlmodel.MetaData:
        return self._syncer.metadata

    @property
    def is_database_syncer(self) -> bool:
        return isinstance(self._syncer, base.DatabaseSyncer)

    def __enter__(self):
        log.debug(f"Registering syncer: {self.protocol.lower()}")

        if self.protocol == "custom":
            _, _, syncer_pathlike = self.protocol.rpartition("@")
            syncer_dir = pathlib.Path(syncer_pathlike)
        else:
            syncer_dir = utils.get_package_directory("cs_tools") / "sync" / self.protocol

        manifest = base.SyncerManifest.model_validate_json(syncer_dir.joinpath("MANIFEST.json").read_text())
        SyncerClass = manifest.import_syncer_class(fp=syncer_dir / "syncer.py")

        if self.definition_fp:
            try:
                conf = toml.load(self.definition_fp)
            except toml.TomlDecodeError as e:
                text = self.definition_fp.read_text()
                line = text.splitlines()[e.lineno - 1]
                trim = line if len(line) < 5 else f"{line[:5]}..."
                raise errors.CSToolsError(
                    f"Could not parse syncer definition syntax, error on line {e.lineno} beginning with '{trim}'"
                    f"\nSyncer definition path:  {self.definition_fp}"
                ) from None
        else:
            conf = {"configuration": self.definition_kw}

        if issubclass(SyncerClass, base.DatabaseSyncer) and self.models is not None:
            conf["configuration"]["models"] = self.models

        log.info(f"Initializing syncer: {SyncerClass}")
        self.__dict__["_syncer"] = SyncerClass(**conf["configuration"])

    def __exit__(self, exc_type, exc_value, exc_traceback):
        if self.is_database_syncer:
            assert isinstance(self._syncer, base.DatabaseSyncer)

            if exc_type is None or isinstance(exc_value, (click.exceptions.Abort, click.exceptions.Exit)):
                self._syncer.session.commit()
                self._syncer.session.close()
            else:
                log.warning(f"Caught Exception, rolling back transaction: {exc_type}: {exc_value}")
                self._syncer.session.rollback()

        return

    def __getattr__(self, member_name: str) -> Any:
        # proxy attribute calls to the underlying syncer first
        try:
            self.__dict__["_syncer"]
            member = getattr(self._syncer, member_name)
        except (KeyError, AttributeError):
            try:
                member = self.__dict__[member_name]
            except KeyError:
                raise AttributeError(f"'{type(self).__name__}' object has no attribute '{member_name}'") from None

        return member

    def __repr__(self) -> str:
        # make the dependency look like the underlying Syncer
        return self._syncer.__repr__()
