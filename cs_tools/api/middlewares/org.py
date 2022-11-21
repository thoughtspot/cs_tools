import json
from httpx import HTTPStatusError

from cs_tools.errors import CSToolsError

class OrgMiddleware:
    """
    Helper functions for dealing with organizations.
    """
    def __init__(self, ts):
        self.ts = ts

    def lookup_id_for_name(self, org_name: str) -> int:
        """
        Looks up the org id for the given name.  IDs are how orgs are managed, but names are more common for users.
        :param org_name: The name of the org to look up the ID for.
        :return: The ID of the org.  Throws an error if the org name doesn't exist.
        """
        try:
            # The following doesn't currently work and gives a 403 for all users.
            # r = self.ts.api.org.get(name=org_name)  # just look for the org with the given name
            # content = json.loads(r.content)
            # return int(content['orgId'])

            # The orgs get call will return the list of orgs the user has access to.
            r = self.ts.api.session.orgs_get()
            orgs = json.loads(r.text).get('orgs')
            for o in orgs:
                if o.get('orgName') == org_name:
                    return o.get('orgId')

            # org not in the results.
            raise(CSToolsError(error=f"Unable to look up org {org_name}",
                               reason=f"Unknown org or user doesn't have access.",
                               mitigation="Verify org exists and user has access."
                              )
                  )

        except HTTPStatusError as hse:
            print(hse)
            raise(CSToolsError(error=f'error getting org ID: {hse}'))
