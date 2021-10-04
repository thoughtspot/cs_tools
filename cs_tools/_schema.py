from dataclasses import dataclass
from typing import List

from ._enums import Privilege


@dataclass
class ThoughtSpotPlatform:
    version: str
    deployment: str
    url: str
    timezone: str
    cluster_name: str
    cluster_id: str

    @classmethod
    def from_session_info(cls, info):
        """
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
    guid: str
    name: str
    display_name: str
    email: str
    privileges: List[Privilege]

    @classmethod
    def from_session_info(cls, info):
        """
        """
        data = {
            'guid': info['userGUID'],
            'name': info['userName'],
            'display_name': info['userDisplayName'],
            'email': info['userEmail'],
            'privileges': info['privileges']
        }

        return cls(**data)
