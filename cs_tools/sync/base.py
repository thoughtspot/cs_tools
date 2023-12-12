from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal, Optional
import functools as ft
import importlib.util
import logging
import pathlib
import sys

from packaging.requirements import Requirement
import pydantic
import sqlalchemy as sa
import sqlmodel

from cs_tools.datastructures import _GlobalModel
from cs_tools.updater._updater import cs_tools_venv

if TYPE_CHECKING:
    from cs_tools.sync.types import TableRows

log = logging.getLogger(__name__)


class PipRequirement(_GlobalModel):
    requirement: Requirement
    pip_args: Optional[list[str]] = pydantic.Field(default_factory=list)

    @pydantic.model_validator(mode="before")
    @classmethod
    def json_tuple_to_dict(cls, data: Any) -> Any:
        if isinstance(data, str):
            return {"requirement": data}

        requirement, *args = data
        return {"requirement": requirement, "pip_args": args}


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
    """A connection to a Data store."""

    __manifest_path__: pathlib.Path = None
    __syncer_name__: str = None

    def __init_subclass__(cls, is_base_class: bool = False):
        super().__init_subclass__()

        if is_base_class:
            return

        # Metaclass-ish wizardry to determine if the Syncer subclass defines the necessary properties.
        if cls.__manifest_path__ is None or cls.__syncer_name__ is None:
            raise NotImplementedError("Syncers must implement both '__syncer_name__' and '__manifest_path__'")

        cls.__ensure_pip_requirements__()
        cls.__init__ = ft.partialmethod(cls.__lifecycle_init__, __original_init__=cls.__init__)

    def __lifecycle_init__(self, *a, __original_init__, **kw):
        """Hook into __init__ so we can call our own post-init function."""
        __original_init__(self, *a, **kw)
        self.__finalize__()

    @classmethod
    def __ensure_pip_requirements__(cls) -> None:
        """Parse the SyncerManifest and install requirements."""
        manifest = SyncerManifest.parse_file(cls.__manifest_path__)

        for requirement in manifest.requirements:
            log.debug(f"Processing requirement: {requirement}")

            if cs_tools_venv.is_package_installed(requirement):
                log.debug("Requirement satisfied, no install necessary")
                continue

            log.info(f"Installing package: {requirement}")
            cs_tools_venv.pip("install", f"{requirement}", *requirement.pip_args)

    @property
    def name(self) -> str:
        """Name of the Syncer."""
        return self.__syncer_name__

    def __finalize__(self) -> None:
        """Will be called after __init__()."""
        pass

    def __repr__(self) -> str:
        return f"<Syncer to '{self.name}'>"

    def load(self, directive: str) -> TableRows:
        """Fetch data from the external data source."""
        raise NotImplementedError(f"There is no default implementation for {self.__class__.__name__}.load")

    def dump(self, directive: str, *, data: TableRows) -> None:
        """Send data to the external data source."""
        raise NotImplementedError(f"There is no default implementation for {self.__class__.__name__}.dump")


class DatabaseSyncer(Syncer, is_base_class=True):
    """A connection to an Database."""

    metadata: sqlmodel.MetaData = sqlmodel.MetaData()
    models: list[pydantic.InstanceOf[sqlmodel.SQLModel]] = pydantic.Field(default_factory=list)
    load_strategy: Literal["APPEND", "TRUNCATE", "UPSERT"] = "UPSERT"

    # To be defined during __init__() by subclasses of the DatabaseSyncer
    _engine: sa.engine.Engine = None

    @property
    def engine(self) -> sa.engine.Engine:
        """The SQLALchemy engine which connects us to our Database."""
        return self._engine

    def __finalize__(self) -> None:
        # Metaclass-ish wizardry to determine if the DatabaseSyncer subclass defines the necessary properties.
        if self._engine is None:
            raise NotImplementedError("DatabaseSyncers must implement a private '_engine'. (sqlalchemy.engine.Engine)")

        if not self.models:
            return

        for model in self.models:
            # If set to None, the schema will be set to that of the schema set on the target MetaData.
            #
            # Further reading:
            #    https://docs.sqlalchemy.org/en/20/core/metadata.html#sqlalchemy.schema.Table.to_metadata.params.schema
            model.__table__.to_metadata(self.metadata, schema=None)

        log.info(f"Creating tables {self.models} in {self}")
        self.metadata.create_all(self.engine, tables=[model.__table__ for model in self.models])

    def __repr__(self) -> str:
        return f"<DatabaseSyncer to '{self.name}'>"
