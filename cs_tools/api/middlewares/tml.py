from __future__ import annotations

from typing import TYPE_CHECKING
from typing import List, Union

from thoughtspot_tml.utils import determine_tml_type
from thoughtspot_tml._tml import TML
from pydantic import validate_arguments

from cs_tools.types import GUID, TMLImportPolicy, TMLSupportedContent, TMLAPIResponse

if TYPE_CHECKING:
    from cs_tools.thoughtspot import ThoughtSpot


class TMLMiddleware:
    """
    Helper functions for dealing with organizations.
    """

    def __init__(self, ts: ThoughtSpot):
        self.ts = ts

    @validate_arguments
    def to_import(
        self,
        tmls: List[Union[TML, str]],
        *,
        policy: TMLImportPolicy = TMLImportPolicy.all_or_none,
        force: bool = False
    ) -> List[TMLAPIResponse]:
        """
        Import TML objects.
        """
        r = self.ts.api.metadata_tml_import(
                import_objects=[t.dumps() if not isinstance(t, str) else t for t in tmls], import_policy=policy
            )

        responses = []

        for tml, content in zip(tmls, r.json()["object"]):
            responses.append(
                TMLAPIResponse(
                    guid=content["response"].get("header", {}).get("id_guid", None),
                    metadata_object_type=TMLSupportedContent.from_friendly_type(tml.tml_type_name).value,
                    tml_type_name=tml.tml_type_name,
                    name=content["response"].get("header", {}).get("name", tml.name),
                    status_code=content["response"]["status"]["status_code"],
                    error_messages=content["response"]["status"].get("error_message", None),
                    _full_response=content,
                )
            )

        return responses

    @validate_arguments
    def to_export(self, guids: List[GUID], *, export_associated: bool=False) -> List[TML]:
        """
        Import TML objects.
        """
        r = self.ts.api.metadata_tml_export(export_guids=guids)

        tmls: List[TML] = []

        for guid, content in zip(guids, r.json()["object"]):
            tml_cls = determine_tml_type(info=content["info"])
            tml = tml_cls.loads(content["edoc"])
            tmls.append(tml)

        return tmls
