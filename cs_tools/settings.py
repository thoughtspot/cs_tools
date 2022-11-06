from ipaddress import IPv4Address
from typing import Union, Dict, Any
import pathlib
import json
import re

from pydantic.types import DirectoryPath, FilePath
from pydantic import BaseModel, AnyHttpUrl, validator
import toml

from cs_tools.errors import ConfigDoesNotExist
from cs_tools.const import APP_DIR
from cs_tools.util import obscure


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
        data = {"default": {"config": None}}

    return data


class Settings(BaseModel):
    """
    Base class for settings management and validation.
    """

    class Config:
        json_encoders = {
            FilePath: lambda v: v.resolve().as_posix(),
            DirectoryPath: lambda v: v.resolve().as_posix()
        }


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
    syncer: Dict[str, FilePath] = None
    verbose: bool = False
    temp_dir: DirectoryPath = APP_DIR

    @validator('syncer')
    def resolve_path(v: Any) -> str:
        if v is None or isinstance(v, dict):
            return v
        return {k: pathlib.Path(f).resolve() for k, f in v.items()}

    @classmethod
    def check_for_default(cls) -> Dict[str, Any]:
        """
        """
        try:
            cfg_data = _meta_config()["default"]["config"]
        except KeyError:
            cfg_data = None

        return cfg_data

    def dict(self) -> Any:
        """
        Wrapper around model.dict to handle path types.
        """
        data = super().json()
        data = json.loads(data)
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

        Parameters
        ----------
        fp : pathlib.Path
          location of the config toml on disk

        verbose, temp_dir
          overrides the settings found in the config file
        """
        try:
            data = toml.load(fp)
        except FileNotFoundError:
            raise ConfigDoesNotExist(name=fp.stem.replace('cluster-cfg_', ''))

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
        Read in a ts-config.toml file by its name.

        If no file is provided, we attempt to check for the default
        configuration.

        Parameters
        ----------
        config: str
          name of the configuration file
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
        Validate initial input from config.create or config.modify.
        """
        _pw = passthru.get('password')
        _syncers = [syncer.split('://') for syncer in passthru.get('syncer', [])]

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
            },
            'syncer': {proto: definition_fp for (proto, definition_fp) in _syncers}
        }

        return cls.parse_obj(data) if validate else cls.construct(**data)
