from typing import List

from pydantic import validate_arguments
import httpx

from cs_tools.data.enums import ConnectionType, GUID, SortOrder


class _Connection:
    """
    Private Connection Services.
    """
    def __init__(self, rest_api):
        self.rest_api = rest_api

    @validate_arguments
    def detail(
        self,
        id: GUID,
        sort: str = SortOrder.default.value,
        sortascending: bool = None,
        pattern: str = None,
        tagname: List[str] = None,
        showhidden: bool = False
    ) -> httpx.Response:

        r = self.rest_api.request(
                'GET',
                f'connection/detail/{id}',
                privacy='private',
                params={
                    "sort": sort,
                    "sortascending": sortascending,
                    "pattern": pattern,
                    "tagname": tagname,
                    "showhidden": showhidden
                }
            )
        return r

    @validate_arguments
    def export(self, id: GUID) -> httpx.Response:
        """Export the yaml info for the connection."""
        r = self.rest_api.request(
            'GET',
            f'connection/export',
            privacy='private',
            params={
                "id": id,
            }
        )
        return r

    @validate_arguments
    def create(self,
               name: str,
               description: str,
               type: ConnectionType,
               createEmpty: bool,
               metadata: str,
               state: int = -1
               ) -> httpx.Response:
        """
        :param name: Name of the connection, e.g. "Retail Data"
        :param description:  Description for the connection, e.g. "Retail data from Snowflake"
        :param type:  The type of connection, e.g. snowflake
        :param createEmpty: Boolean that says if the connection can be empty.  1.7.2+
        :param metadata: The complete definition of the connection (in JSON format).
        :param state:  Totally unknown flag.  # TODO figure this out.
        :return:
        """
        r = self.rest_api.request(
            'POST',
            f'connection/create',
            privacy='private',
            data={
                "name": name,
                "description": description,
                "type": type.value,
                "createEmpty": createEmpty,
                "metadata": metadata,
                "state": state
            }
        )
        return r

    @validate_arguments
    def update(self,
               name: str,
               description: str,
               type: ConnectionType,
               id: GUID,
               createEmpty: bool,
               metadata: str,  # might need a dict.
               state: int = -1
               ) -> httpx.Response:
        """
        :param name: Name of the connection, e.g. "Retail Data"
        :param description:  Description for the connection, e.g. "Retail data from Snowflake"
        :param type:  The type of connection, e.g. snowflake
        :param id: The ID for the connection.
        :param createEmpty: Boolean that says if the connection can be empty.  1.7.2+
        :param metadata: The complete definition of the connection (in JSON format).
        :param state:  Totally unknown flag.  # TODO figure this out.
        :return:
        """
        r = self.rest_api.request(
            'POST',
            f'connection/update',
            privacy='private',
            data={
                "name": name,
                "description": description,
                "type": type.value,
                "id": id,
                "createEmpty": createEmpty,
                "metadata": metadata,
                "state": state
            }
        )
        return r
