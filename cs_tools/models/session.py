import httpx

from cs_tools.models import TSPrivate


class _Session(TSPrivate):
    """
    Security services.
    """

    @property
    def base_url(self):
        """
        Append to the base URL.
        """
        return f'{super().base_url}/session'

    def group_list_user(self, group_id: str) -> httpx.Response:
        """
        List of metadata objects in the repository.
        """
        r = self.get(f'{self.base_url}/group/listuser/{group_id}')
        return r
