from typing import Dict, Any
import pathlib

from pydantic import BaseModel
import toml


class Settings(BaseModel):
    """
    Base class for settings management and validation.
    """


class Auth(Settings):
    """
    Credentials to sign in with.
    """
    username: str
    password: str


class TSInstance(Settings):
    """
    Information about the ThoughtSpot instance.
    """
    host: str
    port: int = None
    disable_ssl: bool = False
    disable_sso: bool = False


class TSConfig(Settings):
    """
    """
    thoughtspot: TSInstance
    auth: Dict[str, Auth]
    logging: Dict[str, Any]

    @classmethod
    def from_toml(cls, fp: pathlib.Path):
        """
        """
        with pathlib.Path(fp).open('r') as t:
            data = toml.load(t)

        return cls.parse_obj(data)


class APIParameters(Settings):
    """
    Base class for API parameter validation.
    """
