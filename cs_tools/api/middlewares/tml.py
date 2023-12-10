from __future__ import annotations

from typing import TYPE_CHECKING, Union
import logging

from pydantic import validate_arguments
from thoughtspot_tml.utils import determine_tml_type
import httpx

from cs_tools.types import GUID, TMLAPIResponse, TMLImportPolicy, TMLSupportedContent

if TYPE_CHECKING:
    from thoughtspot_tml._tml import TML

    from cs_tools.thoughtspot import ThoughtSpot

log = logging.getLogger(__name__)


class TMLMiddleware:
    """
    Helper functions for dealing with organizations.
    """

    def __init__(self, ts: ThoughtSpot):
        self.ts = ts

    # @validate_arguments
    def to_import(
        self, tmls: list[Union[TML, str]], *, policy: TMLImportPolicy = TMLImportPolicy.all_or_none, force: bool = False
    ) -> list[TMLAPIResponse]:
        """
        Import TML objects.
        """
        r = self.ts.api.v1.metadata_tml_import(
            import_objects=[t.dumps() if not isinstance(t, str) else t for t in tmls],
            import_policy=policy,
            force_create=force,
        )

        responses = []

        for tml, content in zip(tmls, r.json()["object"]):
            response = TMLAPIResponse(
                guid=content["response"].get("header", {}).get("id_guid", None),
                metadata_object_type=TMLSupportedContent.from_friendly_type(tml.tml_type_name).value,
                tml_type_name=tml.tml_type_name,
                name=content["response"].get("header", {}).get("name", tml.name),
                status_code=content["response"]["status"]["status_code"],
                error_messages=content["response"]["status"].get("error_message", None),
            )
            response._full_response = content
            responses.append(response)

        return responses

    @validate_arguments
    def to_export(
        self,
        guids: list[GUID],
        *,
        export_associated: bool = False,
        iterator: bool = False,
    ) -> list[TML]:
        """
        Import TML objects.
        """
        # DEV NOTE: @boonhapus, 2023/01/24
        #
        #   running individual exports is not efficient, how can we provide a better API for customers with large
        #   amount of content ot export?
        #
        tmls: list[TML] = []

        for guid in guids:
            try:
                r = self.ts.api.v1.metadata_tml_export(export_guids=[guid], export_associated=export_associated)

                for content in r.json().get("object", []):
                    info = content["info"]

                    if info["status"]["status_code"] == "ERROR":
                        r.status_code = 417
                        m = f"417: hijacked by CS Tools, response from API: {info['status'].get('error_message', None)}"
                        raise httpx.HTTPStatusError(m, request=r.request, response=r)

                    tml_cls = determine_tml_type(info=content["info"])
                    tml = tml_cls.loads(content["edoc"])

                    if iterator:
                        yield tml

                    tmls.append(tml)

            except httpx.HTTPStatusError as e:
                log.warning(f"{guid} could not be exported, see log for details..")
                log.debug(e, exc_info=True)
                continue

        return tmls
