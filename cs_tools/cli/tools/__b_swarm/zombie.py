from typing import Any, Dict
import datetime as dt
import asyncio
import logging
import random
import json

from horde.zombies.httpx import HTTPXZombie
import horde
import httpx

from cs_tools.types import GUID, MetadataObjectType
from cs_tools.types import LoggedInUser

log = logging.getLogger(__name__)


class ThoughtSpotPerformanceEvent(horde.Event):
    __slots__ = ("metadata_type", "guid", "user", "responses")

    def __init__(
        self,
        source,
        metadata_type: MetadataObjectType,
        guid: GUID,
        user: LoggedInUser,
        responses: Dict[GUID, httpx.Response],
    ):
        super().__init__(source)
        self.metadata_type = metadata_type
        self.guid = guid
        self.user = user
        self.responses = responses

    @property
    def is_success(self) -> bool:
        """Whether or not the API calls were successful."""
        return all(r.is_success for r in self.responses.values())

    @property
    def request_start_time(self) -> dt.datetime:
        if self.metadata_type == "QUESTION_ANSWER_BOOK":
            response = list(self.responses.values())[0]

        if self.metadata_type == "PINBOARD_ANSWER_BOOK":
            response = list(self.responses.values())[0]

        return dt.datetime.fromisoformat(response.request.headers["x-requested-at"])

    @property
    def response_received_time(self) -> dt.datetime:
        if self.metadata_type == "QUESTION_ANSWER_BOOK":
            response = list(self.responses.values())[0]

        if self.metadata_type == "PINBOARD_ANSWER_BOOK":
            response = list(self.responses.values())[-1]

        return dt.datetime.fromisoformat(response.request.headers["x-requested-at"]) + response.elapsed

    @property
    def latency(self) -> dt.timedelta:
        """Full load time of the object."""
        if self.metadata_type == "QUESTION_ANSWER_BOOK":
            elapsed = list(self.responses.values())[0].elapsed

        if self.metadata_type == "PINBOARD_ANSWER_BOOK":
            first = list(self.responses.values())[0]
            last = list(self.responses.values())[-1]
            beg = dt.datetime.fromisoformat(first.request.headers["x-requested-at"])
            end = dt.datetime.fromisoformat(last.request.headers["x-requested-at"]) + last.elapsed
            elapsed = end - beg

        return elapsed


async def add_request_sent_timestamp(request: httpx.Request) -> None:
    """Add on the timestamp."""
    request.headers["x-requested-at"] = dt.datetime.now(tz=dt.UTC).isoformat()


class ThoughtSpotZombie(HTTPXZombie):

    def __init__(self, environment, zombie_id: int):
        super().__init__(environment, zombie_id)
        self.client.event_hooks["request"].append(add_request_sent_timestamp)
        self.client.timeout = 600
        self.client.headers.update({"user-agent": "python-requests/9.9.9", "x-requested-by": "CS Tools"})
        self.user: LoggedInUser = None
        self.my_content: Dict[str, GUID] = {"answers": [], "liveboards": []}

        if not hasattr(self.horde.shared_state, "liveboard_viz_cache"):
            self.horde.shared_state.liveboard_viz_cache = {}

    async def get_user(self) -> str:
        """Return a random user from the pool of available users."""
        return random.choice(self.horde.shared_state.all_users)

    async def get_visualization_guids(self, *, guid: GUID) -> Any:
        """Find the vizIds for a given liveboard."""
        try:
            d = self.horde.shared_state.liveboard_viz_cache[guid]
        except KeyError:
            p = {"id": guid}
            r = await self.client.get("callosum/v1/tspublic/v1/metadata/listvizheaders", params=p)
            d = r.json()

            if r.is_success:
                self.horde.shared_state.liveboard_viz_cache[guid] = d

        return d

    async def get_accessible_content(self, *, metadata_type: MetadataObjectType) -> None:
        content = []

        while True:
            p = {
                "type": metadata_type,
                "chunksize": 500,
                "offset": len(content),
                "showhidden": False,
                "auto_created": False
            }

            r = await self.client.get("callosum/v1/tspublic/v1/metadata/list", params=p)
            d = r.json()
            content.extend([{"metadata_type": metadata_type, **metadata} for metadata in d["headers"]])

            if d["isLastBatch"]:
                break

        return content

    #
    #
    #

    async def on_start(self) -> None:
        # 1. Grab an unused User
        # 2. Login
        # 3. Set the Zombie to their name.
        # 4. Get their accessible content.
        user = await self.get_user()
        self._name = user["name"]

        # LOGIN TOKEN
        d = {"secret_key": self.horde.shared_state.secret_key, "username": user["name"], "access_level": "FULL"}
        r = await self.client.post("callosum/v1/tspublic/v1/session/auth/token", data=d)

        # AUTH
        d = {"auth_token": r.text, "username": user["name"]}
        r = await self.client.post("callosum/v1/tspublic/v1/session/login/token", data=d)

        # INFO
        r = await self.client.get("callosum/v1/tspublic/v1/session/info")
        self.user = LoggedInUser.from_api_v1_session_info(r.json())

        # CONTENT
        self.my_content["answers"] = await self.get_accessible_content(metadata_type="QUESTION_ANSWER_BOOK")
        self.my_content["liveboards"] = await self.get_accessible_content(metadata_type="PINBOARD_ANSWER_BOOK")

    async def on_stop(self):
        await self.client.post("callosum/v1/tspublic/v1/session/logout")

    #
    #
    #

    async def v1_answer(self, guid: GUID) -> None:
        """Visit a Saved Answer."""
        d = {"type": "QUESTION_ANSWER_BOOK", "id": guid, "batchsize": "5000"}
        f = {k: (None, v) for k, v in d.items()}
        r = await self.client.post("callosum/v1/data/reportbook", files=f)

        event = ThoughtSpotPerformanceEvent(
                    source=self,
                    metadata_type="QUESTION_ANSWER_BOOK",
                    guid=guid,
                    user=self.user,
                    responses={guid: r}
                )
        
        self.environment.events.fire(event)

    async def v1_liveboard(self, guid: GUID) -> None:
        """Visit a Liveboard."""
        mapped_coros = {}
        visualizations = await self.get_visualization_guids(guid=guid)

        for visualization in visualizations:
            if visualization["vizType"] not in ("CHART", "TABLE"):
                continue

            viz_id = visualization["id"]
            d = {"type": "PINBOARD_ANSWER_BOOK", "id": guid, "vizid": json.dumps([viz_id]), "batchsize": "5000"}
            f = {k: (None, v) for k, v in d.items()}
            mapped_coros[viz_id] = self.client.post("callosum/v1/data/reportbook", files=f)

        responses = await asyncio.gather(*mapped_coros.values(), return_exceptions=True)

        event = ThoughtSpotPerformanceEvent(
                    source=self,
                    metadata_type="PINBOARD_ANSWER_BOOK",
                    guid=guid,
                    user=self.user,
                    responses=dict(zip(mapped_coros, responses))
                )

        self.environment.events.fire(event)
