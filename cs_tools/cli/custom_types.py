from __future__ import annotations

from collections.abc import Sequence
from typing import Any
import datetime as dt
import logging
import pathlib
import urllib

from awesomeversion import AwesomeVersion, AwesomeVersionStrategy, AwesomeVersionStrategyException
import click
import pydantic
import toml

from cs_tools import datastructures, utils
from cs_tools.sync import base

log = logging.getLogger(__name__)


class CustomType(click.ParamType):
    """
    A distinct type for use on the CLI.

    Is used as a click_type, but without the explicit instance creation.
    """

    name = "CUSTOM_TYPE"

    def convert(self, value: Any, param: click.Parameter | None, ctx: click.Context | None) -> Any:
        """Take raw input string and converts it to the desired type."""
        raise NotImplementedError


class Literal(CustomType):
    """Only accept one of a few choices."""

    def __init__(self, choices: Sequence[str]) -> None:
        self.choices = choices

    def get_metavar(self, param: click.Parameter) -> str:  # noqa: ARG002
        """Example usage of the parameter to display on the CLI."""
        return "|".join(self.choices)

    def convert(self, value: Any, param: click.Parameter | None, ctx: click.Context | None) -> str:
        """Validate that the CLI input is one of the accepted values."""
        original_value = value
        choices = self.choices

        if ctx is not None and ctx.token_normalize_func is not None:
            value = ctx.token_normalize_func(value)
            choices = [ctx.token_normalize_func(choice) for choice in self.choices]

        if value not in choices:
            self.fail(
                message=f"Invalid value, should be one of {self.choices}, got '{original_value}'",
                param=param,
                ctx=ctx,
            )

        return original_value


class Version(CustomType):
    """Convert STR to AwesomeVersion."""

    name = "VERSION"

    def __init__(self, strategy: AwesomeVersionStrategy = AwesomeVersionStrategy.SIMPLEVER) -> None:
        self.strategy = strategy

    def convert(self, value: Any, param: click.Parameter | None, ctx: click.Context | None) -> AwesomeVersion:
        """Coerce strings into a awesomeversion.AwesomeVersion."""
        try:
            version = AwesomeVersion(value, ensure_strategy=self.strategy)
        except AwesomeVersionStrategyException:
            self.fail(message=f"Invalid format, '{value}' is not a valid {self.strategy.name}.", param=param, ctx=ctx)

        return version


class Date(CustomType):
    """Convert STR to DATE."""

    def get_metavar(self, param: click.Parameter) -> str:  # noqa: ARG002
        """Example usage of the parameter to display on the CLI."""
        return "YYYY-MM-DD"

    def convert(self, value: Any, param: click.Parameter | None, ctx: click.Context | None) -> dt.date:
        """Coerce ISO-8601 date strings into a datetime.datetime.date."""
        try:
            date = dt.date.fromisoformat(value)
        except ValueError:
            self.fail(message="Invalid format, please use YYYY-MM-DD", param=param, ctx=ctx)

        return date


class Directory(CustomType):
    """Convert STR to DIRECTORY PATH."""

    def __init__(self, exists: bool = False, make: bool = False):
        self.exists = exists
        self.make = make

    def get_metavar(self, param: click.Parameter) -> str:  # noqa: ARG002
        """Example usage of the parameter to display on the CLI."""
        return "DIRECTORY"

    def convert(self, value: Any, param: click.Parameter | None, ctx: click.Context | None) -> pathlib.Path:
        """Coerce string into a pathlib.Path.is_dir()."""
        try:
            path = pydantic.TypeAdapter(pydantic.DirectoryPath).validate_python(value)
        except pydantic.ValidationError as e:
            self.fail(message="\n".join(_["msg"] for _ in e.errors()), param=param, ctx=ctx)

        if self.exists and not path.exists():
            self.fail(message="Directory does not exist", param=param, ctx=ctx)

        if self.make:
            path.mkdir(parents=True, exist_ok=True)

        return path.resolve()


class Syncer(CustomType):
    """Convert STR to Syncer."""

    def __init__(self, models: list[datastructures.ValidatedSQLModel] | None = None):
        self.models = models

    def _parse_syncer_configuration(
        self, definition_spec: str, param: click.Parameter | None, ctx: click.Context | None
    ) -> dict[str, Any]:
        try:
            assert ".toml" in definition_spec, "Syncer definition is not a TOML file, it's likely given as declarative."
            options = toml.load(definition_spec)
            options = options["configuration"]

        except AssertionError:
            query_string = urllib.parse.urlparse(f"proto://?{definition_spec}").query
            options = {k: vs[0] for k, vs in urllib.parse.parse_qs(query_string).items()}

        except FileNotFoundError:
            self.fail(message=f"Syncer definition file does not exist at '{definition_spec}'.", param=param, ctx=ctx)

        except toml.TomlDecodeError:
            log.debug(f"Syncer definition file '{definition_spec}' is invalid TOML.", exc_info=True)
            self.fail(message=f"Syncer definition file '{definition_spec}' is invalid TOML.", param=param, ctx=ctx)

        return options

    def get_metavar(self, param: click.Parameter) -> str:  # noqa: ARG002
        """Example usage of the parameter to display on the CLI."""
        return "protocol://DEFINITION.toml"

    def convert(self, value: Any, param: click.Parameter | None, ctx: click.Context | None) -> base.Syncer:
        """Coerce string into a Syncer."""
        CS_TOOLS_PKG_DIR = utils.get_package_directory("cs_tools")

        protocol, _, definition_spec = value.partition("://")

        # fmt: off
        log.debug(f"Registering syncer: {protocol.lower()}")
        syncer_base_dir = CS_TOOLS_PKG_DIR / "sync" / protocol
        syncer_manifest = base.SyncerManifest.model_validate_json(syncer_base_dir.joinpath("MANIFEST.json").read_text())
        syncer_options  = self._parse_syncer_configuration(definition_spec, param=param, ctx=ctx)
        # fmt: on

        SyncerClass = syncer_manifest.import_syncer_class(fp=syncer_base_dir / "syncer.py")

        if issubclass(SyncerClass, base.DatabaseSyncer) and self.models is not None:
            syncer_options["models"] = self.models

        log.info(f"Initializing syncer: {SyncerClass}")
        return SyncerClass(**syncer_options)

        # if self.is_database_syncer:
        #     assert isinstance(self._syncer, base.DatabaseSyncer)

        #     if exc_type is None or isinstance(exc_value, (click.exceptions.Abort, click.exceptions.Exit)):
        #         self._syncer.session.commit()
        #         self._syncer.session.close()
        #     else:
        #         log.warning(f"Caught Exception, rolling back transaction: {exc_type}: {exc_value}")
        #         self._syncer.session.rollback()
class MultipleInput(CustomType):
    """Expand a single input into a list of inputs."""

    name = "TEXT"

    def __init__(self, sep: str = ",", *, type_caster: type = str):
        self.sep = sep
        self.type_caster = type_caster
    
    def convert(self, value: Any, param: click.Parameter | None, ctx: click.Context | None) -> list[Any]:
        """Coerce string into an iterable of <type_caster>."""
        if isinstance(value, str):
            values = value.split(self.sep)

        elif isinstance(value, collections.abc.Iterable):
            values = [v.split(",") if isinstance(v, str) else v for v in value]

        try:
            values = [self.type_caster(v) for v in values]
        except Exception:
            log.debug(f"Could not coerce all values to '{self.type_caster}', {values}", exc_info=True)
            self.fail(message=f"Could not coerce all values to '{self.type_caster}', {values}", param=param, ctx=ctx)

        return values
    
    def __contains__(self, value: Any) -> bool:
        """Only here to make the typer checker happy."""
        raise NotImplementedError("MultipleInput is not meant to be instantiated directly, use .convert() instead.")
