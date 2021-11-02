from ipaddress import IPv4Address
from typing import Union, Dict, Any
import pathlib
import re

from pydantic import BaseModel, AnyHttpUrl, validator
import typer
import toml

from cs_tools.helpers.secrets import obscure


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
        config=None,
        *,
        host,
        username,
        default=True,
        interactive=False,
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

        default : bool, default: True
          whether or not to take default args if they're not provided

        interactive : bool, default: False
          wether or not to gather user input if required args not supplied

        **kw
          additional arguments to provide to TSConfig
        """
        if config is not None:
            app_dir = pathlib.Path(typer.get_app_dir('cs_tools'))
            cfg = cls.from_toml(app_dir / f'cluster-cfg_{config}.toml')

            if host is not None:
                cfg.thoughtspot.host = host

            if kw.get('disable_sso', False):
                cfg.thoughtspot.disable_sso = kw['disable_sso']

            if kw.get('disable_ssl', False):
                cfg.thoughtspot.disable_ssl = kw['disable_ssl']

            if kw.get('verbose', False):
                cfg.verbose = kw['verbose']

            return cfg

        if interactive:
            if host is None:
                host = typer.prompt('host')

            if username is None:
                username = typer.prompt('username')

            if kw.get('password') is None:
                kw['password'] = typer.prompt('password', hide_input=True)

        data = {
            'verbose': kw['verbose'] if kw.get('verbose') is not None else False,
            'thoughtspot': {
                'host': host,
                'port': kw.get('port', None),
                'disable_ssl': kw['disable_ssl'] if kw.get('disable_ssl') is not None else False,
                'disable_sso': kw['disable_sso'] if kw.get('disable_sso') is not None else False,
            },
            'auth': {
                'frontend': {
                    'username': username,
                    # NOTE: if we need real security, we can simply replace obscure()
                    'password': None if kw.get('password') is None else obscure(kw['password'])
                }
            }
        }

        return cls(**data)
