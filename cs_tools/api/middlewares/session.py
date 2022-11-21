import json
from typing import Union
from httpx import HTTPStatusError

from cs_tools.errors import CSToolsError


class SessionMiddleware:
    """
    Helper functions for dealing with organizations.
    """
    def __init__(self, ts):
        self.ts = ts

    def switch_org(self, org: Union[str, int]) -> int:
        """
        Looks up the org id for the given name.  IDs are how orgs are managed, but names are more common for users.
        :param org: The name or ID to switch to.
        :return: The ID of the org.  Throws an error if the org name or ID doesn't exist or you can't switch.
        """
        try:
            # assuming people don't name the orgs with numbers.
            orgid = -1

            if isinstance(org, str):
                # first see if it can be converted to an int.  If so, then assume it's an ID.
                try:
                    orgid = int(org)
                except:
                    orgid = self.ts.org.lookup_id_for_name(org)

            r = self.ts.api.session.orgs_put(orgid=orgid)

            return org
        except HTTPStatusError as hse:
            print(hse)
            if hse.response.status_code == 403:  # permission error.
                error_details = json.loads(hse.response.text).get('debug', 'Unknown reason')
                raise (CSToolsError(error=f'Error setting org context.',
                                    reason=f"{error_details}",
                                    mitigation=f"Verify the org name or ID and try again."))

            else:
                raise (CSToolsError(error=f'error switching to org : {hse}',
                                    reason=f"Invalid {'name' if isinstance(org, str) else 'ID'} specified",
                                    mitigation=f"Verify the org name or ID and try again."))
