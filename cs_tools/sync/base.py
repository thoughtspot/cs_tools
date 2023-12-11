from __future__ import annotations

from typing import TYPE_CHECKING, Optional
import importlib
import logging
import pathlib
import sys

import pydantic
import sqlalchemy as sa
import sqlmodel

from cs_tools._compat import StrEnum
from cs_tools.datastructures import _GlobalModel
from cs_tools.updater._updater import cs_tools_venv

if TYPE_CHECKING:
    from cs_tools.sync.types import TableRows

log = logging.getLogger(__name__)


class DatabaseLoadStrategy(StrEnum):
    APPEND = "append"
    TRUNCATE = "truncate"
    UPSERT = "upsert"


class PipRequirement(_GlobalModel):
    library: str
    version: str
    pip_args: list[str] = pydantic.Field(default_factory=list)


class SyncerManifest(_GlobalModel):
    name: str
    syncer_class: str
    requirements: Optional[list[PipRequirement]] = pydantic.Field(default_factory=list)

    def import_syncer_class(self, fp: pathlib.Path) -> Syncer:
        __name__ = f"cs_tools_{fp.parent.stem}_syncer"  # noqa: A001
        __file__ = fp
        __path__ = [fp.parent.as_posix()]

        spec = importlib.util.spec_from_file_location(__name__, __file__, submodule_search_locations=__path__)
        module = importlib.util.module_from_spec(spec)

        # add to already-loaded modules, so further imports within each directory will work
        sys.modules[__name__] = module

        spec.loader.exec_module(module)
        return getattr(module, self.syncer_class)


class Syncer(_GlobalModel):
    """"""

    __manifest_path__ = None
    __syncer_name__ = None

    def __init_subclass__(cls, is_base_class: bool = False):
        super().__init_subclass__()

        if is_base_class:
            return

        if cls.__manifest_path__ is None or cls.__syncer_name__ is None:
            raise NotImplementedError("Syncers must implement both '__syncer_name__' and '__manifest_path__'")

        cls.__ensure_installed__()
        cls.__init__ = cls.__deferred__(cls.__init__)

    @classmethod
    def __deferred__(cls, __original_init__):
        """ """

        def __lifecycle_init__(self, *a, **kw):
            __original_init__(self, *a, **kw)

            if hasattr(self, "__register__"):
                self.__register__()

        return __lifecycle_init__

    @classmethod
    def __ensure_installed__(cls) -> None:
        manifest = SyncerManifest.parse_file(cls.__manifest_path__)

        for requirement in manifest.requirements:
            log.debug(f"processing requirement: {requirement.library}")

            if cs_tools_venv.is_package_installed(requirement):
                log.debug("requirement satisfied, no install necessary")
                continue

            log.info(f"installing package: {requirement.library}")
            cs_tools_venv.pip("install", f"{requirement.library} == {requirement.version}", *requirement.pip_args)

    @property
    def name(self) -> str:
        return self.__syncer_name__

    def load(self, directive: str) -> TableRows:
        raise NotImplementedError(f"There is no default implementation for {self.__class__.__name__}.load")

    def dump(self, directive: str, *, data: TableRows) -> None:
        raise NotImplementedError(f"There is no default implementation for {self.__class__.__name__}.dump")


class DatabaseSyncer(Syncer, is_base_class=True):
    """ """

    metadata: sqlmodel.MetaData = sqlmodel.MetaData()
    models: list[pydantic.InstanceOf[sqlmodel.main.SQLModelMetaclass]] = None
    load_strategy: DatabaseLoadStrategy = DatabaseLoadStrategy.UPSERT

    @property
    def engine(self) -> sa.engine.Engine:
        return self._engine

    @property
    def connection(self):
        return self._connection

    def __register__(self) -> None:
        if not self.models:
            return

        for model in self.models:
            # If set to None, the schema will be set to that of the schema set on the target MetaData.
            #
            # Further reading:
            #    https://docs.sqlalchemy.org/en/20/core/metadata.html#sqlalchemy.schema.Table.to_metadata.params.schema
            model.__table__.to_metadata(self.metadata, schema=None)

        log.info(f"Creating tables {self.models} in {self}")
        self.metadata.create_all(self.connection, tables=[model.__table__ for model in self.models])
