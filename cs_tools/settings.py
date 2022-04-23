from ipaddress import IPv4Address
from typing import Union, Dict, Any
import pathlib
import re

from pydantic.types import DirectoryPath
from pydantic import BaseModel, AnyHttpUrl, validator
import toml

from cs_tools.util import obscure
from cs_tools.const import APP_DIR


def _meta_config(config_name: str = None) -> Union[str, Dict[str, Any]]:
    """
    Read or write to the meta config.

    The Meta Config file is pretty simple.

    [default]
    config = 'my-config-name'
    """
    mode = 'r' if config_name is None else 'w'

    try:
        with (APP_DIR / '.meta-config.toml').open(mode=mode) as j:
            if config_name is not None:
                data = toml.dump({'default': {'config': config_name}}, j)
            else:
                data = toml.load(j)
    except FileNotFoundError:
        data = {}

    return data


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
    name: str
    thoughtspot: HostConfig
    auth: Dict[str, AuthConfig]
    verbose: bool = False
    temp_dir: DirectoryPath = APP_DIR

    def dict(self) -> Any:
        """
        Wrapper around model.dict to handle path types.
        """
        data = super().dict()

        try:
            data['temp_dir'] = data['temp_dir'].resolve().as_posix()
        except AttributeError:
            pass

        return data

    @classmethod
    def from_toml(
        cls,
        fp: pathlib.Path,
        *,
        verbose: bool = None,
        temp_dir: pathlib.Path = None
    ) -> 'TSConfig':
        """
        Read in a ts-config.toml file.
        """
        data = toml.load(fp)

        if data.get('name') is None:
            data['name'] = fp.stem.replace('cluster-cfg_', '')

        # overrides
        if verbose is not None:
            data['verbose'] = verbose

        if temp_dir is not None:
            data['temp_dir'] = temp_dir

        return cls.parse_obj(data)

    @classmethod
    def from_command(cls, config: str = None, **passthru) -> 'TSConfig':
        """
        """
        if config is None:
            meta = _meta_config(config)
            config = meta['default']['config']

        return cls.from_toml(APP_DIR / f'cluster-cfg_{config}.toml', **passthru)

    @classmethod
    def from_parse_args(
        cls,
        name: str,
        *,
        validate: bool = True,
        **passthru
    ) -> 'TSConfig':
        """
        """
        _pw = passthru.get('password')

        data = {
            'name': name,
            'verbose': passthru.get('verbose'),
            'temp_dir': passthru.get('temp_dir'),
            'thoughtspot': {
                'host': passthru['host'],
                'port': passthru.get('port'),
                'disable_ssl': passthru.get('disable_ssl'),
                'disable_sso': passthru.get('disable_sso'),
            },
            'auth': {
                'frontend': {
                    'username': passthru['username'],
                    'password': obscure(_pw).decode() if _pw is not None else _pw
                }
            }
        }
        return cls.parse_obj(data) if validate else cls.construct(**data)
