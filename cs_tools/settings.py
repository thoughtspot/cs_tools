from ipaddress import IPv4Address
from typing import Union, Dict, Any
import pathlib

from pydantic import BaseModel, AnyUrl, validator
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


class HostConfig(Settings):
    host: Union[AnyUrl, IPv4Address]
    port: int = None
    disable_ssl: bool = False
    disable_sso: bool = False

    @validator('host')
    def cast_as_str(v: Any) -> str:
        """
        Converts arguments to a string.
        """
        return str(v)


class AuthConfig(Settings):
    username: str
    password: str = None


# class LogLevel(str, enum.Enum):
#     debug = 'DEBUG'
#     info = 'INFO'
#     warn = 'WARN'
#     error = 'ERROR'
#     critical = 'CRITICAL'


# class LoggerConfig(Settings):
#     level: LogLevel = LogLevel.info

#     class Config:
#         use_enum_values = True


class TSConfig(Settings):
    thoughtspot: HostConfig
    auth: Dict[str, AuthConfig]
    # logging: LoggerConfig

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
        validate=True,
        interactive=False,
        **kw
    ) -> ['TSConfig', dict]:
        """
        Build TSConfig from command line arguments.
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

            return cfg

        if interactive:
            if host is None:
                host = typer.prompt('host')

            if username is None:
                username = typer.prompt('username')

            if kw.get('password') is None:
                kw['password'] = typer.prompt('password', hide_input=True)

        data = {
            'thoughtspot': {
                'host': host,
                'port': kw.get('port', None),
                'disable_ssl': kw.get('disable_ssl') or False,
                'disable_sso': kw.get('disable_sso') or False
            },
            'auth': {
                'frontend': {
                    'username': username,
                    # NOTE: if we need real security, we can simply replace obscure()
                    'password': kw.get('password', None) or obscure(kw['password'])
                }
            }
            # 'logging': {
            #     'level': kw.get('logger', None) or 'INFO'
            # }
        }

        if not validate:
            return cls.construct(**data)

        return cls(**data)
