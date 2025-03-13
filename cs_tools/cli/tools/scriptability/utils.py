from __future__ import annotations

from typing import Any, Literal, Optional, Union
import datetime as dt
import json
import logging
import os
import pathlib
import re

import pydantic
import rich
import thoughtspot_tml

from cs_tools import _types

from . import api_transformer

_LOG = logging.getLogger(__name__)

RE_ENVVAR_STRUCTURE = re.compile(r"\$\{\{\s*env\.(?P<envvar>[A-Za-z0-9_]+)\s*\}\}", flags=re.MULTILINE)
"""Variable structure looks like ${{ env.MY_VAR_NAME }} and can be inline with other text."""


def is_allowed_object(
    metadata_object: _types.APIResult,
    allowed_types: list[_types.MetadataObjectType],
    disallowed_system_users: list[_types.GUID],
) -> bool:
    """Determines if an object is allowed to be EXPORTED or IMPORTED."""
    if "TABLE" in allowed_types:
        allowed_types.append("ONE_TO_ONE_LOGICAL")
        allowed_types.append("USER_DEFINED")

    if "VIEW" in allowed_types:
        allowed_types.append("AGGR_WORKSHEET")

    if "MODEL" in allowed_types:
        allowed_types.append("WORKSHEET")

    #
    #
    #

    if metadata_object["author_guid"] in disallowed_system_users:
        return False

    if "ALL" in allowed_types:
        return True

    if metadata_object["object_type"] in allowed_types:
        return True

    if metadata_object["object_type"] == "LOGICAL_TABLE":
        return metadata_object["object_subtype"] in allowed_types

    return False


class MappingCheckpoint(pydantic.BaseModel):
    """Metadata about the export/import process."""

    by: str
    """Who or What made the checkpoint."""

    at: dt.datetime
    """When the checkpoint was recorded, held as an ISO8601 formatted UTC datetime."""

    mode: Literal["EXPORT", "VALIDATE", "IMPORT"]
    """The mode of the checkpoint."""

    status: _types.TMLStatusCode
    """The status of the checkpoint.. OK, WARNING, or ERROR."""

    info: dict[str, Any] = pydantic.Field(default={})
    """Arbitrary information about what happened."""

    @pydantic.field_serializer("at")
    @classmethod
    def serialize_datetime(self, value: Optional[dt.datetime]) -> Optional[str]:
        return None if value is None else value.isoformat()


class GUIDMappingInfo(pydantic.BaseModel, extra=pydantic.Extra.forbid):
    """
    Wrapper for guid mapping to make it easier to use.

    !! DO NOT INSTANTIATE THIS DIRECTLY !!

    Instead, call GUIDMappingInfo.load(path: Optional[pathlib.Path])
    """

    metadata: dict[str, Any] = pydantic.Field(default={})
    """Arbitrary / informational metadata about this environment."""

    mapping: dict[_types.GUID, Optional[_types.GUID]] = pydantic.Field(default={})
    """An automatically maintained mapping of GUIDs between two environments which are swapped before IMPORT."""

    additional_mapping: dict[str, str] = pydantic.Field(default={})
    """Any additional string references which should be swapped in IMPORT."""

    history: list[MappingCheckpoint] = pydantic.Field(default=[])
    """A log of all the checkpoints which have been made."""

    _path: Optional[pathlib.Path] = None
    """Where to write the GUIDMapping."""

    @classmethod
    def load(cls, path: Optional[pathlib.Path] = None) -> GUIDMappingInfo:
        """Load the GUID mapping info."""
        try:
            assert path is not None, "--> raise FileNotFoundError"
            info = cls.parse_obj(json.loads(path.read_text(encoding="utf-8")))

        except pydantic.ValidationError:
            raise

        except (AssertionError, FileNotFoundError):
            info = cls()

        info._path = path

        return info

    @classmethod
    def merge(cls, *, source: pathlib.Path, target: pathlib.Path) -> GUIDMappingInfo:
        """Merge two GUID mappings, handling conflicts."""
        # DEV NOTE: @boonhapus, 2025/02/20
        #   Q. Why do we need this?
        #   A. While git helps you manage conflicts between branches natively, Users typically do not understand how to
        #      handle merge conflicts. While the filesystem managed by scriptability is not a git repository, it
        #      operates very much in the same way.
        #
        #      Additionally, the fs/repo are mirrors of the external ThoughtSpot
        #      system which is allowed to pace as far ahead as it wants. That said, ThoughtSpot has no knowledge of the
        #      fs/git repo, and ThoughtSpot Data Manager will perform parallel development.
        #
        #      This merge-mapping flow is intended to help alleviae these common git-merge conflicts prior to a commit.
        #      By combining EXTRACT.history and IMPORT.history, we can piece together parallel workloads from different
        #      branches.
        #
        MAX_NUM_CHECKPOINTS = 300
        """An arbitrary magic number. High enough to handle parallel 'commit early and often' development workflows."""

        source_env = cls.load(path=source)
        target_env = cls.load(path=target)

        # WARN THE USER IF THEY ARE TRYING TO MERGE GUID MAPPINGS FROM DIFFERENT EXTRACT ENVIRONMENTS.
        # THE PURPOSE OF GUID MAPPING IS TO ENSURE THE SAME OBJECTS FROM EXTRACT ALWAYS HIT THE SAME OBJECTS IN TARGET.
        #
        if "cs_tools" in target_env.metadata:
            extract_source = source_env.metadata["cs_tools"]["extract_environment"]
            extract_target = target_env.metadata["cs_tools"]["extract_environment"]

            if extract_source != extract_target:
                _LOG.warning(
                    f"The target environment already has an extract environment of '{extract_target}' but you provided "
                    f"'{extract_source}'. Did you mean to merge for a different project?"
                )
                raise RuntimeError("Cannot merge GUID mappings from different extract environments.")

        # DEV NOTE: @boonhapus, 2025/02/20
        #   If there are duplicate keys, the value from the right-hand dictionary takes precedence.

        # COPY THE METADATA (preferring SOURCE environment).
        target_env.metadata = target_env.metadata | source_env.metadata

        # MERGE THE BASE MAPPINGS (preferring TARGET environment).
        target_env.mapping = source_env.mapping | target_env.mapping

        # MERGE THE ADDITIONAL MAPPINGS (preferring TARGET environment).
        target_env.additional_mapping = source_env.additional_mapping | target_env.additional_mapping

        # MERGE THE HISTORY (keeping only the K latest).
        target_env.history = sorted(source_env.history + target_env.history, key=lambda x: x.at)[:MAX_NUM_CHECKPOINTS]

        return target_env

    def checkpoint(
        self,
        *,
        by: str,
        mode: Literal["EXPORT", "VALIDATE", "IMPORT"],
        environment: str,
        status: _types.TMLStatusCode,
        info: Optional[dict[str, Any]] = None,
    ) -> None:
        """Checkpoint the GUID mapping info."""
        if mode != "EXPORT" and not any(checkpoint.mode in ("EXPORT", "VALIDATE") for checkpoint in self.history):
            raise RuntimeError(f"Cannot {mode} without an EXPORT.")

        self.history.append(
            MappingCheckpoint(
                by=by,
                at=dt.datetime.now(tz=dt.timezone.utc),
                mode=mode,
                environment=environment,
                status=status,
                info=info,
            )
        )

    def disambiguate(self, tml: _types.TMLObject, delete_unmapped_guids: bool = True) -> _types.TMLObject:
        """Disambiguate an incoming TML object."""
        # ADDITIONAL MAPPING NEEDS TO COME FIRST, IN CASE WE DELETE A GUID DURING DISAMBIGUATION.
        if self.additional_mapping:
            try:
                text = original = tml.dumps(format_type="YAML")

                for to_find, to_replace in self.additional_mapping.items():
                    # PRE-PROCESS TO FETCH ENVIRONMENT VARIABLES, WITH FALLBACK TO THE ORIGINAL VALUE.
                    if match := RE_ENVVAR_STRUCTURE.search(to_replace):
                        # the whole matched string ............... ${{ env.MY_VAR_NAME }}
                        envvar_template = match.group(0)
                        # just the value name .................... MY_VAR_NAME
                        envvar_name = match.group("envvar")
                        # fetch the value from os.environ ........ anything~
                        envvar_value = os.getenv(envvar_name, envvar_template)

                        to_replace = to_replace.replace(envvar_template, envvar_value)

                    # PERFORM STRING REPLACEMENTS VIA EXACT MATCH (case sensitive)
                    if to_find in text:
                        _LOG.info(f"Replacing '{to_find}' with '{to_replace}' in {tml.name} ({tml.tml_type_name})")
                        text = text.replace(to_find, to_replace)

                if text != original:
                    tml = tml.loads(text)

            except (IndexError, thoughtspot_tml.exceptions.TMLDecodeError) as e:
                # JUST FALL BACK TO TML WITH THE VARIABLES IN IT, WHICH SHOULD FAIL ON TML IMPORT ANYWAY.
                _LOG.warning(f"Could not variablize '{tml.name}' ({tml.tml_type_name}), see logs for details..")
                _LOG.debug(e, exc_info=True)

                if hasattr(e, "parent_exc"):
                    _LOG.debug(f"due to..\n{e}", exc_info=True)

                _LOG.info(f"TML MODIFIED STATE:\n\n{text}")
                raise

        # STANDARD DISMABIGUATION
        tml = thoughtspot_tml.utils.disambiguate(
            tml=tml,
            guid_mapping=self.mapping,
            remap_object_guid=True,
            delete_unmapped_guids=delete_unmapped_guids,
        )

        return tml

    def map_guid(self, *, old: _types.GUID, new: _types.GUID, disallow_overriding: bool = True) -> None:
        """Map a GUID."""
        if old not in self.mapping:
            _LOG.warning(f"Old GUID {old} not found in the mapping, setting anyway..")

        if (already_mapped := self.mapping.get(old, None)) is None:
            self.mapping[old] = new

        elif already_mapped == new:
            pass

        elif disallow_overriding:
            _LOG.warning(f"Old GUID {old} already mapped to {already_mapped}, skipping..")

        else:
            _LOG.warning(f"Old GUID {old} already mapped to {already_mapped}, overriding..")
            self.mapping[old] = new

    def save(self, new_path: Optional[pathlib.Path] = None) -> None:
        """Saves the GUID mappings."""
        if new_path is None and self._path is None:
            raise ValueError("No save path provided.")

        if new_path is not None:
            self._path = new_path

        assert self._path is not None, "This should be unreachable. GUIDMappingInfo requires a path."

        self._path.write_text(self.model_dump_json(indent=2), encoding="utf-8")


class TMLStatus(pydantic.BaseModel):
    operation: Literal["EXPORT", "VALIDATE", "IMPORT"]
    edoc: Optional[str] = None
    metadata_guid: Optional[_types.GUID] = None
    metadata_name: Optional[str] = None
    metadata_type: Union[_types.UserFriendlyObjectType, Literal["WORKSHEET"], Literal["UNKNOWN"]] = "UNKNOWN"
    status: _types.TMLStatusCode
    message: Optional[str] = None
    _raw: dict

    @pydantic.field_validator("metadata_type", mode="before")
    @classmethod
    def ensure_uppercase(cls, value: str) -> str:
        """Ensure the metadata type is uppercase."""
        return value.upper() if value is not None else value

    @pydantic.field_validator("message", mode="before")
    @classmethod
    def conform_newlines(cls, value: str) -> Optional[str]:
        """Some TML errors have <br/> tags instead of standard newlines."""
        if value is None:
            return None

        return value.replace("<br/>", "\n")

    @property
    def cleaned_messages(self) -> list[str]:
        """The .message proprty is the raw result from the API."""
        # An example message from the API as of 10.5.0.cl ..
        #
        # TS_GROUP_MEMBERSHIP_to_TS_EFFECTIVE_GROUP_PRIVILEGES: Skipped relationship import as there are no tables with
        # id 612c8bdb-ff19-40cb-bffb-fe287dbb2705 in CS Tools. <br/><br/>cs_tools - user_mapping_to_TS_GROUP_MEMBERSHIP:
        # Skipped relationship import as there are no tables with id 5d15ad5b-0a67-4a2c-b16c-c0bb9f3d44a8 in CS Tools.
        # <br/>
        #
        # Which is actually multiple messages/warnings/errors in one. We transform that into.
        #
        # [
        #     "TS_GROUP_MEMBERSHIP_to_TS_EFFECTIVE_GROUP_PRIVILEGES: Skipped relationship import as there are no "
        #     "tables with id 612c8bdb-ff19-40cb-bffb-fe287dbb2705 in CS Tools.",
        #
        #     "cs_tools - user_mapping_to_TS_GROUP_MEMBERSHIP: Skipped relationship import as there are no tables with "
        #     "id 5d15ad5b-0a67-4a2c-b16c-c0bb9f3d44a8 in CS Tools."
        # ]
        #
        if self.message is None:
            return []
        return [m.strip() for m in self.message.split("\n\n")]

    @property
    def color(self) -> str:
        """Fetch the status color which represents the success of the tml response."""
        status_colors = {
            "ERROR": "fg-error",
            "WARNING": "fg-warn",
            "OK": "fg-success",
        }

        return status_colors[self.status]

    @property
    def emoji(self) -> str:
        """Fetch the status emoji which represents the success of the tml response."""
        # fmt: off
        status_emojis = {
            "ERROR": ":x:",                 # ❌
            "WARNING": ":rotating_light:",  # 🚨
            "OK": ":white_check_mark:",     # ✅
        }
        # fmt: on

        return status_emojis[self.status]


class TMLOperations:
    """Represents a job of TML operations."""

    def __init__(
        self,
        data: list[_types.APIResult],
        *,
        domain: Literal["SCRIPTABILITY", "GITHUB"],
        op: Literal["EXPORT", "VALIDATE", "IMPORT"],
        policy: Optional[_types.TMLImportPolicy] = None,
    ):
        self._data = data
        self.domain = domain
        self.operation = op
        self.policy = policy

        if op == "EXPORT":
            reshaped = api_transformer.tml_export_status(data)
        else:
            reshaped = api_transformer.tml_import_status(data, operation=op)

        self._statuses = [TMLStatus(**_) for _ in reshaped]

    @property
    def statuses(self) -> list[TMLStatus]:
        """Return a list of parsed TML statuses."""
        return self._statuses

    @property
    def can_map_guids(self) -> bool:
        """Determine if the statuses' GUIDs should be mapped."""
        # GUIDs are returned, but we shouldn't map them since nothing actually imported.
        if self.operation == "VALIDATE":
            return False

        # GUIDs should not be returned if any object failed during an ALL_OR_NONE import.
        if self.policy == "ALL_OR_NONE" and self.job_status != "OK":
            return False

        # All objects failed to IMPORT.
        if all(_.status == "ERROR" for _ in self.statuses):
            return False

        # In this case, at least GUID has returned, EVEN IF the whole job was marked as a failure.
        # We may have up to 1 failure or 1 warning causing the job to be marked this way.
        return True

    @property
    def job_status(self) -> _types.TMLStatusCode:
        """The aggregate status of the TML operation."""
        any_error = any(_.status == "ERROR" for _ in self.statuses)
        any_warn = any(_.status == "WARNING" for _ in self.statuses)

        if self.policy == "ALL_OR_NONE" and (any_error or any_warn):
            return "ERROR"

        if any_error:
            return "ERROR"

        if any_warn:
            return "WARNING"

        return "OK"

    @property
    def job_status_color(self) -> str:
        status_colors = {
            "ERROR": "fg-error",
            "WARNING": "fg-warn",
            "OK": "fg-success",
        }
        return status_colors[self.job_status]

    def __str__(self) -> str:
        """Represent the trimmed results as JSON."""
        results = [
            {
                "status": response.status,
                "metadata_type": response.metadata_type,
                "metadata_guid": response.metadata_guid,
                "metadata_name": response.metadata_name,
                "message": response.message,
            }
            for response in self.statuses
        ]
        return json.dumps(results, indent=4)

    def __rich__(self) -> rich.console.ConsoleRenderable:
        """Generate a pretty table."""
        # fmt: off
        t = rich.table.Table(box=rich.box.SIMPLE_HEAD, row_styles=("dim", ""), width=150)
        t.add_column("",     width= 1 + 4, justify="center")  # .. LENGTH OF EMOJI + 4 padding
        t.add_column("Type", width=10 + 4)  # .................... LENGTH OF "CONNECTION" (the longest type) + 4 padding
        t.add_column("GUID", width=36 + 4)  # .................... LENGTH OF A UUID + 4 padding
        t.add_column("Name", width=24 + 4, no_wrap=True)  # ...... ARBITRARY LENGTH, long enough to understand the NAME
        t.add_column("Message", width=150 - 5 - 14 - 40 - 28, no_wrap=True)
        # fmt: on

        for response in self.statuses:
            n = len(response.cleaned_messages)
            s = "" if n <= 1 else "s"

            t.add_row(
                response.emoji,
                response.metadata_type,
                response.metadata_guid,
                response.metadata_name,
                f"{n} issue{s}, use --log-errors for details" if n else "",
            )

        policy = "" if self.policy is None else f" [dim]. POLICY :: {self.policy}[/]"

        r = rich.panel.Panel(
            t,
            title="TML Status",
            subtitle=f"TML / {self.domain.upper()} / {self.operation}{policy}",
            subtitle_align="right",
            border_style=self.job_status_color,
        )

        return r
