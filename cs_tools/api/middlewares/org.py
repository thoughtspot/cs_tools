from __future__ import annotations

from typing import TYPE_CHECKING, Union
import json

import httpx

from cs_tools.errors import CSToolsError

if TYPE_CHECKING:
    from cs_tools.thoughtspot import ThoughtSpot


class OrgMiddleware:
    """
    Helper functions for dealing with organizations.
    """

    def __init__(self, ts: ThoughtSpot):
        self.ts = ts

    def get(self, org_name: str) -> int:
        """
        Looks up the org id for the given name.

        Normally this would be .guid_for, but Orgs don't have GUIDs, they have simple
        numeric IDs.
        """
        r = self.ts.api.v1.session_orgs_read()

        for org in r.json().get("orgs", []):
            if org["orgName"] == org_name:
                return org.get("orgId")

        raise CSToolsError(
            title=f"Invalid Org passed '{org_name}'",
            reason="Org is unknown or the User doesn't have access to it.",
            mitigation="Verify the Org exists and that the User has access.",
        )

    def switch(self, org: Union[str, int]) -> int:
        """
        Switch to the target org.

        Parameters
        ----------
        org : str, int
          name or ID of the org to switch to

        Raises
        ------
        CSToolsError
          raise when no matching org is found, or you're disallowed from switching
        """
        org_id = org if str(org).lstrip("-").isdigit() else self.get(org)

        try:
            self.ts.api.v1.session_orgs_update(org_id=org_id)

        except httpx.HTTPStatusError as e:
            if e.response.status_code == httpx.codes.FORBIDDEN:
                rzn = json.loads(e.response.text).get("debug", "Unknown reason")
            else:
                rzn = f"Invalid org specified, got '{org}'"

            raise CSToolsError(
                title=f"Error setting org context for org {org}.",
                reason=rzn,
                mitigation="Verify the org name or ID and try again.",
            ) from None

        return org_id
