from typing import Any, Dict, List, Union
import logging

from pydantic.dataclasses import dataclass

from ._enums import Privilege


log = logging.getLogger(__name__)


@dataclass
class ThoughtSpotPlatform:
    """
    Information about the ThoughtSpot deployment.
    """
    version: str
    deployment: str
    url: str
    timezone: str
    cluster_name: str
    cluster_id: str

    @classmethod
    def from_session_info(cls, info: Dict[str, Any]):
        """
        Form a User from the session/info response.
        """
        data = {
            'version': info['releaseVersion'],
            'deployment': 'cloud' if info['configInfo']['isSaas'] else 'software',
            'url': info['configInfo']['emailConfig']['welcomeEmailConfig']['getStartedLink'],
            'timezone': info['timezone'],
            'cluster_name': info['configInfo']['selfClusterName'],
            'cluster_id': info['configInfo']['selfClusterId'],
        }

        return cls(**data)


@dataclass
class LoggedInUser:
    """
    Information about the currently authenticed user.
    """
    guid: str
    name: str
    display_name: str
    email: str
    # Sometimes we get weird NULL privilege in data.. so we'll just accept some others
    privileges: List[Union[Privilege, str, int]]

    @classmethod
    def from_session_info(cls, info: Dict[str, Any]):
        """
        Form a User from the session/info response.
        """
        data = {
            'guid': info['userGUID'],
            'name': info['userName'],
            'display_name': info['userDisplayName'],
            'email': info['userEmail'],
            'privileges': info['privileges']
        }

        return cls(**data)
