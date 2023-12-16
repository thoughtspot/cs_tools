from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import logging
import pathlib

import click
import sqlmodel

from cs_tools.cli.dependencies.base import Dependency
from cs_tools.const import PACKAGE_DIR
from cs_tools.sync import base

log = logging.getLogger(__name__)


@dataclass
class DSyncer(Dependency):
    protocol: str
    definition_fp: pathlib.Path = None
    definition_kw: dict[str, Any] = None
    models: list[sqlmodel.SQLModel] = None

    @property
    def metadata(self) -> sqlmodel.MetaData:
        """"""
        return self._syncer.metadata

    def __enter__(self):
        log.info(f"Registering syncer: {self.protocol}")

        if self.protocol == "custom":
            _, _, syncer_pathlike = self.protocol.rpartition("@")
            syncer_dir = pathlib.Path(syncer_pathlike)
        else:
            syncer_dir = PACKAGE_DIR / "sync" / self.protocol

        manifest_path = syncer_dir / "MANIFEST.json"
        manifest = base.SyncerManifest.parse_file(manifest_path)

        SyncerClass = manifest.import_syncer_class(fp=manifest_path.parent / "syncer.py")

        ctx = click.get_current_context()

        if self.definition_fp:
            conf = self._read_config_from_definition(ctx.obj.thoughtspot, self.protocol, self.definition_fp)
        else:
            conf = {"configuration": self.definition_kw}

        if issubclass(SyncerClass, base.DatabaseSyncer) and self.models is not None:
            conf["configuration"]["models"] = self.models

        log.debug(f"Initializing syncer: {SyncerClass}")
        self._syncer = SyncerClass(**conf["configuration"])

    def __exit__(self, *e):
        # https://stackoverflow.com/a/58984188
        if isinstance(self._syncer, base.DatabaseSyncer) and hasattr(self._syncer, "_cnxn"):
            if hasattr(self._syncer._cnxn, "close"):
                self._syncer._cnxn.close()

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

    # def _read_config_from_definition(self, ts, proto, definition) -> Dict[str, Any]:
    #     if definition in ("default", ""):
    #         try:
    #             definition = ts.config.syncer[proto]
    #         except (TypeError, KeyError):
    #             raise SyncerError(
    #                 proto=proto,
    #                 cfg=ts.config.name,
    #                 reason="No default definition has been set for this cluster config.",
    #                 mitigation=(
    #                     "Pass the full path to [primary]{proto}://[/] or set a default "
    #                     "with [primary]cs_tools config modify --config {cfg} --syncer "
    #                     "{proto}://[blue]path/to/my/default.toml"
    #                 ),
    #             )

    #     if definition.as_posix().endswith("toml"):
    #         try:
    #             cfg = toml.load(definition)
    #         except UnicodeDecodeError:
    #             back = r"C:\work\my\example\filepath".replace("\\", "\\\\")
    #             fwds = r"C:\work\my\example\filepath".replace("\\", "/")
    #             raise SyncerError(
    #                 proto=proto,
    #                 definition=definition,
    #                 reason="Couldn't read the Syncer definition at [blue]{definition}[/]",
    #                 mitigation=(
    #                     f"If you're on Windows, you must escape the backslashes in your filepaths, or flip them the "
    #                     f"other way around."
    #                     f"\n"
    #                     r"\n  :cross_mark: [red]C:\work\my\example\filepath[/]"
    #                     f"\n  :white_heavy_check_mark: [green]{back}[/]"
    #                     f"\n  :white_heavy_check_mark: [green]{fwds}[/]"
    #                 ),
    #             )
    #         except toml.TomlDecodeError:
    #             raise SyncerError(
    #                 proto=proto,
    #                 proto_url=proto.lower(),
    #                 definition=definition,
    #                 reason="Your definition file [blue]{definition}[/] is not correct.",
    #                 mitigation=(
    #                     "Visit the link below to see a full example."
    #                     "\n[blue]https://thoughtspot.github.io/cs_tools/syncer/{proto_url}/#full-definition-example"
    #                 ),
    #             )

    #     return cfg

    # def __Syncer_init__(self, Syncer, **syncer_config):
    #     try:
    #         # sanitize input by accepting aliases
    #         if hasattr(Syncer, "__pydantic_model__"):
    #             syncer_config = Syncer.__pydantic_model__.parse_obj(syncer_config).dict()

    #         self._syncer = Syncer(**syncer_config)
    #     except KeyError:
    #         raise SyncerError(
    #             proto=self.protocol,
    #             definition=self.definition_fp,
    #             reason="[blue]{definition}[/] is missing a top level marker.",
    #             mitigation=(r"The first line of your definition file should be..\n\n[white]\[configuration]"),
    #         )
    #     except pydantic.ValidationError as e:
    #         raise SyncerError(
    #             proto=self.protocol,
    #             proto_url=self.protocol.lower(),
    #             definition=self.definition_fp or "CLI Input",
    #             errors="\n  ".join([f"[blue]{_['loc'][0]}[/]: {_['msg']}" for _ in e.errors()]),
    #             reason="[blue]{definition}[/] has incorrect parameters.\n\n  {errors}",
    #             mitigation=(
    #                 "Visit the link below to see a full example."
    #                 "\n[blue]https://thoughtspot.github.io/cs_tools/syncer/{proto_url}/#full-definition-example"
    #             ),
    #         )
