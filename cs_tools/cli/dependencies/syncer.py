from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List
import pathlib
import logging

import sqlmodel
import pydantic
import click
import toml

from cs_tools.cli.dependencies.base import Dependency
from cs_tools.errors import SyncerError
from cs_tools.const import PACKAGE_DIR
from cs_tools.sync import register

log = logging.getLogger(__name__)


@dataclass
class DSyncer(Dependency):
    protocol: str
    definition_fp: pathlib.Path = None
    definition_kw: Dict[str, Any] = None
    models: List[sqlmodel.SQLModel] = None

    @property
    def metadata(self) -> sqlmodel.MetaData:
        """
        Priority ->
          1. metadata defined on the syncer instance
          2. metadata defined in the SQLModel layer
          3. fallback metadata
        """

        if hasattr(self._syncer, "metadata"):
            return self._syncer.metadata

        if self.models is not None:
            return self.models[0].metadata

        if not hasattr(self, "_metadata"):
            self._metadata = sqlmodel.MetaData()

        return self._metadata

    def __enter__(self):
        # TODO: registation as part of __init_subclass__, now that we're a real package~
        log.info(f"registering syncer: {self.protocol}")
        manifest = PACKAGE_DIR / "sync" / self.protocol / "MANIFEST.json"
        Syncer = register.load_syncer(protocol=self.protocol, manifest_path=manifest)

        ctx = click.get_current_context()

        if self.definition_fp:
            cfg = self._read_config_from_definition(ctx.obj.thoughtspot, self.protocol, self.definition_fp)
        else:
            cfg = {"configuration": self.definition_kw}

        log.debug(f"initializing syncer: {Syncer}")
        self.__Syncer_init__(Syncer, **cfg["configuration"])

        if hasattr(self._syncer, "__is_database__") and self.models is not None:
            log.debug(f"creating tables {self.models} in {self._syncer}")
            [t.__table__.to_metadata(self.metadata) for t in self.models if t.metadata is not self.metadata]
            self.metadata.create_all(self._syncer.cnxn, tables=[t.__table__ for t in self.models])

    def __exit__(self, *e):
        # reserved for shutdown work if we need to tidy up the database?
        return

    #
    # MAKE THE DEPENDENCY BEHAVE LIKE A SYNCER
    #

    def __getattr__(self, member_name: str) -> Any:
        # proxy calls to the underlying syncer first
        try:
            member = getattr(self._syncer, member_name)
        except AttributeError:
            try:
                member = self.__dict__[member_name]
            except KeyError:
                raise AttributeError(f"'{type(self).__name__}' object has no attribute '{member_name}'") from None

        return member

    def __repr__(self) -> str:
        # make the dependency look like the underlying Syncer
        return self._syncer.__repr__()

    #
    #
    #

    def _read_config_from_definition(self, ts, proto, definition) -> Dict[str, Any]:
        if definition in ("default", ""):
            try:
                definition = ts.config.syncer[proto]
            except (TypeError, KeyError):
                raise SyncerError(
                    proto=proto,
                    cfg=ts.config.name,
                    reason="No default definition has been set for this cluster config.",
                    mitigation=(
                        "Pass the full path to [primary]{proto}://[/] or set a default "
                        "with [primary]cs_tools config modify --config {cfg} --syncer "
                        "{proto}://[blue]path/to/my/default.toml"
                    ),
                )

        if definition.endswith("toml"):
            try:
                cfg = toml.load(definition)
            except UnicodeDecodeError:
                back = r"C:\work\my\example\filepath".replace("\\", "\\\\")
                fwds = r"C:\work\my\example\filepath".replace("\\", "/")
                raise SyncerError(
                    proto=proto,
                    definition=definition,
                    reason="Couldn't read the Syncer definition at [blue]{definition}[/]",
                    mitigation=(
                        f"If you're on Windows, you must escape the backslashes in your filepaths, or flip them the "
                        f"other way around."
                        f"\n"
                        r"\n  :cross_mark: [red]C:\work\my\example\filepath[/]"
                        f"\n  :white_heavy_check_mark: [green]{back}[/]"
                        f"\n  :white_heavy_check_mark: [green]{fwds}[/]"
                    ),
                )
            except toml.TomlDecodeError:
                raise SyncerError(
                    proto=proto,
                    definition=definition,
                    reason="Your definition file [blue]{definition}[/] is not correct.",
                    mitigation=(
                        "Visit the link below to see a full example."
                        "\n[blue]https://thoughtspot.github.io/cs_tools/syncer/{proto}/#full-definition-example"
                    ),
                )

        return cfg

    def __Syncer_init__(self, Syncer, **syncer_config):
        try:
            # sanitize input by accepting aliases
            if hasattr(Syncer, "__pydantic_model__"):
                syncer_config = Syncer.__pydantic_model__.parse_obj(syncer_config).dict()

            self._syncer = Syncer(**syncer_config)
        except KeyError:
            raise SyncerError(
                proto=self.protocol,
                definition=self.definition_fp,
                reason="[blue]{definition}[/] is missing a top level marker.",
                mitigation=(r"The first line of your definition file should be..\n\n[white]\[configuration]"),
            )
        except pydantic.ValidationError as e:
            raise SyncerError(
                proto=self.protocol,
                definition=self.definition_fp,
                errors="\n  ".join([f"[blue]{_['loc'][0]}[/]: {_['msg']}" for _ in e.errors()]),
                reason="[blue]{definition}[/] has incorrect parameters.\n\n  {errors}",
                mitigation=(
                    "Visit the link below to see a full example."
                    "\n[blue]https://thoughtspot.github.io/cs_tools/syncer/{proto}/#full-definition-example"
                ),
            )
