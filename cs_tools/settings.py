from ipaddress import IPv4Address
from typing import Union, Dict, Any
import pathlib
import json
import re

from pydantic.types import DirectoryPath
from pydantic import BaseModel, AnyHttpUrl, validator
import typer
import toml

from cs_tools.helpers.secrets import obscure
from cs_tools.const import APP_DIR


class Settings(BaseModel):
    """
    Base class for settings management and validation.
    """


class APIParameters(Settings):
    """
    Base class for API parameter validation.
    """


class TSCloudURL(str):
    """
    Validator to match against a ThoughtSpot cloud URL.
    """
    REGEX = re.compile(r'(?:https:\/\/)?(.*\.thoughtspot\.cloud)(?:\/.*)?')

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not isinstance(v, str):
            raise TypeError('string required')

        m = cls.REGEX.fullmatch(v)

        if not m:
            raise ValueError('invalid thoughtspot cloud url')

        return cls(f'{m.group(1)}')


class LocalHost(str):
    """
    Validator to match against localhost.
    """
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if v != 'localhost':
            raise ValueError('value is not localhost')

        return cls(v)


class HostConfig(Settings):
    host: Union[AnyHttpUrl, IPv4Address, TSCloudURL, LocalHost]
    port: int = None
    disable_ssl: bool = False
    disable_sso: bool = False

    @property
    def fullpath(self):
        host = self.host
        port = self.port

        if not host.startswith('http'):
            host = f'https://{host}'

        if port:
            port = f':{port}'
        else:
            port = ''

        return f'{host}{port}'

    @validator('host')
    def cast_as_str(v: Any) -> str:
        """
        Converts arguments to a string.
        """
        if hasattr(v, 'host'):
            return f'{v.scheme}://{v.host}'

        return str(v)


class AuthConfig(Settings):
    username: str
    password: str = None


class TSConfig(Settings):
    thoughtspot: HostConfig
    auth: Dict[str, AuthConfig]
    verbose: bool = False
    temp_dir: DirectoryPath = APP_DIR

    def dict(self) -> Any:
        """
        Wrapper around model.dict to handle path types.
        """
        data = super().dict()

        if data['temp_dir'] is not None:
            data['temp_dir'] = data['temp_dir'].resolve().as_posix()

        return data

    @classmethod
    def from_toml(cls, fp: pathlib.Path):
        """
        Read in a ts-config.toml file.
        """
        with pathlib.Path(fp).open('r') as t:
            data = toml.load(t)

        return cls.parse_obj(data)

    @classmethod
    def from_cli_args(
        cls,
        config: str = None,
        *,
        host: str,
        username: str,
        interactive: bool = False,
        validate: bool = True,
        **kw
    ) -> ['TSConfig', dict]:
        """
        Build TSConfig from command line arguments.

        Parameters
        ----------
        config : str
          name of the config file to parse

        host : str
          url of the thoughtspot frontend

        interactive : bool, default: False
          whether or not to gather user input if required args not supplied

        validate : bool, default True
          whether or not to validate input

        **kw
          additional arguments to provide to TSConfig
        """
        if config is not None:
            cfg = cls.from_toml(APP_DIR / f'cluster-cfg_{config}.toml')

            # single-command overrides
            if kw.get('verbose', False):
                cfg.verbose = kw['verbose']

            if kw.get('temp_dir', False):
                cfg.temp_dir = kw['temp_dir']

            return cfg

        if interactive:
            if host is None:
                host = typer.prompt('host')

            if username is None:
                username = typer.prompt('username')

            if kw.get('password') is None:
                kw['password'] = typer.prompt('password', hide_input=True)

        data = {
            'verbose': kw.get('verbose'),
            'temp_dir': kw.get('temp_dir'),
            'thoughtspot': {
                'host': host,
                'port': kw.get('port', None),
                'disable_ssl': kw.get('disable_ssl'),
                'disable_sso': kw.get('disable_sso'),
            },
            'auth': {
                'frontend': {
                    'username': username,
                    # NOTE: if we need real security, we can simply replace obscure()
                    'password': None if kw.get('password') is None else obscure(kw['password'])
                }
            }
        }

        if not validate:
            return cls.construct(**data)

        return cls(**data)
