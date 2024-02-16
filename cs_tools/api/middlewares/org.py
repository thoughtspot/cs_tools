from __future__ import annotations

from typing import TYPE_CHECKING, Union
import logging

from cs_tools import errors

if TYPE_CHECKING:
    from cs_tools.thoughtspot import ThoughtSpot

log = logging.getLogger(__name__)


class OrgMiddleware:
    """
    Helper functions for dealing with organizations.
    """

    def __init__(self, ts: ThoughtSpot):
        self.ts = ts

    def guid_for(self, org: Union[str, int]) -> int:
        """
        Looks up the org id for the given name.

        Orgs don't technically have GUIDs, but randomly assigned BIGINTs instead.
        """
        r = self.ts.api.v1.session_orgs_read()

        for org_info in r.json().get("orgs", []):
            if str(org) in map(str, [org_info["orgId"], org_info["orgName"]]):
                return org_info.get("orgId")

        raise errors.CSToolsCLIError(
            title=f"Invalid Org passed '{org}'",
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
        CSToolsCLIError
          raise when no matching org is found, or you're disallowed from switching
        """
        if not self.ts.session_context.thoughtspot.is_orgs_enabled:
            log.warning(f"Org {org} specified but this cluster is not enabled for orgs, ignoring..")
            return -1

        org_id = self.guid_for(org)

        try:
            self.ts.config.thoughtspot.default_org = org_id
            self.ts.login()

        except errors.AuthenticationError:
            raise errors.CSToolsCLIError(
                title=f"Error setting org context for org {org}.",
                reason=f"Invalid org specified, got '{org}'",
                mitigation="Verify the org name or ID and try again.",
            ) from None

        return org_id
