import json

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
            r = self.ts.api.org.get(name=org_name)  # just look for the org with the given name
            content = json.loads(r.content)
            return int(content['orgId'])
        except Exception as e:
            print(e)
            raise(CSToolsError(f'error getting org ID: {e}'))
