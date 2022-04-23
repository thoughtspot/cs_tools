from tempfile import TemporaryDirectory
import logging.config
import subprocess as sp
import datetime as dt
import platform
import logging
import pathlib
import shutil

from typer import Argument as A_, Option as O_  # noqa
import oyaml as yaml
import typer

from cs_tools.cli.tools.common import setup_thoughtspot
from cs_tools.cli.dependency import depends
from cs_tools.cli._loader import _gather_tools
from cs_tools.cli.options import CONFIG_OPT
from cs_tools._version import __version__
from cs_tools.cli.ux import console, CSToolsGroup, CSToolsCommand
from cs_tools.errors import CSToolsException
from cs_tools.const import APP_DIR

from .app_config import app as cfg_app
from .app_log import app as log_app
from .tools import app as tools_app


log = logging.getLogger(__name__)


app = typer.Typer(
    cls=CSToolsGroup,
    name="cs_tools",
    help="""
    Welcome to CS Tools!

    These are scripts and utilities used to assist in the development,
    implementation, and administration of your ThoughtSpot platform.

    All tools are provided as-is. While every effort has been made to
    test and certify use of these tools in the various supported
    ThoughtSpot deployments, each environment is different!

    [bold yellow]You should ALWAYS take a snapshot before you make any
    significant changes to your environment![/]

    \b
    [green]For additional help, please visit our documentation![/]
    [blue]https://thoughtspot.github.io/cs_tools/[/]
    """,
    add_completion=False,
    context_settings={
        # global settings
        'help_option_names': ['--help', '-h', '--helpfull'],

        # allow responsive console design
        'max_content_width':
            console.width if console.width <= 120 else max(120, console.width * .65),

        # allow case-insensitive commands
        'token_normalize_func': lambda x: x.lower()
    },
    options_metavar='[--version, --help]'
)


@app.command('platform', cls=CSToolsCommand, hidden=True)
@depends(
    thoughtspot=setup_thoughtspot,
    options=[CONFIG_OPT],
    enter_exit=True
)
def _platform(ctx: typer.Context):
    """
    Return details about this machine for debugging purposes.
    """
    ts = ctx.obj.thoughtspot

    console.print(f"""[yellow]
        [PLATFORM DETAILS]
        system: {platform.system()} (detail: {platform.platform()})
        python: {platform.python_version()}
        ran at: {dt.datetime.now(dt.timezone.utc).astimezone().strftime('%Y-%m-%d %H:%M:%S%z')}
        cs_tools: v{__version__}

        [THOUGHTSPOT]
        cluster id: {ts.platform.cluster_id}
        cluster: {ts.platform.cluster_name}
        url: {ts.platform.url}
        timezone: {ts.platform.timezone}
        branch: {ts.platform.deployment}
        version: {ts.platform.version}

        [LOGGED IN USER]
        user_id: {ts.me.guid}
        username: {ts.me.name}
        display_name: {ts.me.display_name}
        privileges: {list(map(lambda e: e.name, ts.me.privileges))}
    """)


@app.command('build-docs', cls=CSToolsCommand, hidden=True)
def _docs_build(
    dir_: pathlib.Path = A_(..., metavar='DIR', help='directory to output the documentation to'),
    zipped: bool = O_(False, '--zipped', help='compress the documentation into a single zipfile')
):
    """
    Build the documentation offline.

    [yellow]You must have a development install in order to run this command![/]
    """
    try:
        import mkdocs  # noqa
    except ModuleNotFoundError:
        log.error(
            'You do not have a development install of cs_tools, please see the project '
            'maintainers for an offline version of the documentation.'
        )
        raise typer.Exit(-1)

    PROJECT_ROOT = pathlib.Path(__file__).parent.parent.parent
    TMP_DIR  = TemporaryDirectory()
    TMP_FILE = pathlib.Path(TMP_DIR.name) / 'local.yaml'

    if zipped:
        dir_ = dir_ / 'docs'

    with (PROJECT_ROOT / 'mkdocs.yml').open('r') as remote, TMP_FILE.open('w') as local:
        data = yaml.load(remote.read(), Loader=yaml.Loader)
        # should also remove plugins.search when/if we enable it
        data['docs_dir'] = (PROJECT_ROOT / 'docs').as_posix()
        data['site_url'] = ''
        data['use_directory_urls'] = False
        yaml.dump(data, local)

        # -f, --config-file  Provide a specific MkDocs config
        # -d, --site-dir     The directory to output the result of the documentation build.
        with sp.Popen(f'mkdocs build -f {TMP_FILE} -d {dir_}', stdout=sp.PIPE) as p:
            for line in p.stdout:
                log.info(line)

    if zipped:
        shutil.make_archive(dir_.parent / f'cs_tools-docs-{__version__}', 'zip', dir_)
        shutil.rmtree(dir_)


def _clean_logs(now):
    logs_dir = APP_DIR / 'logs'
    logs_dir.mkdir(parents=True, exist_ok=True)

    # keep only the last 25 logfiles
    lifo = sorted(logs_dir.iterdir(), reverse=True)

    for idx, log in enumerate(lifo):
        if idx > 25:
            log.unlink()


def run():
    """
    Entrypoint into cs_tools.
    """
    _gather_tools(tools_app)
    app.add_typer(tools_app)
    app.add_typer(cfg_app)
    app.add_typer(log_app)

    # SETUP LOGGING
    now = dt.datetime.now().strftime('%Y-%m-%dT%H_%M_%S')
    _clean_logs(now)

    logging.config.dictConfig({
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'verbose': {
                'format': '[%(levelname)s - %(asctime)s] [%(name)s - %(module)s.%(funcName)s %(lineno)d] %(message)s'
            }
        },
        'handlers': {
            'to_file': {
                'formatter': 'verbose',
                'level': 'DEBUG',     # user can override in their config file
                'class': 'logging.FileHandler',
                # RotatingFileHandler.__init__ params...
                'filename': f'{APP_DIR}/logs/{now}.log',
                'mode': 'w',          # Create a new file for each run of cs_tools.
                'encoding': 'utf-8',  # Handle unicode fun.
                'delay': True         # Don't create a file if no logging is done.
            },
            'to_console': {
                'level': 'INFO',
                'class': 'rich.logging.RichHandler',
                # rich.__init__ params...
                'console': console,
                'show_level': False,
                'markup': True,
                'log_time_format': '[%X]'
            }
        },
        'loggers': {},
        'root': {
            'level': 'DEBUG',
            'handlers': ['to_file', 'to_console']
        }
    })

    logging.getLogger('urllib3').setLevel(logging.ERROR)
    logging.getLogger('httpx').setLevel(logging.ERROR)

    try:
        app()
    except Exception as e:
        log.debug('whoopsie, something went wrong!', exc_info=True)

        if isinstance(e, CSToolsException):
            log.info(f'[error]{e.cli_message}')
        else:
            GF = 'https://forms.gle/sh6hyBSS2mnrwWCa9'
            GH = 'https://github.com/thoughtspot/cs_tools/issues/new/choose'

            log.exception(
                '[yellow]This is an unhandled error!! 😅'
                '\n\nIf you encounter this message more than once, please help by '
                'letting us know at one of the links below:'
                f'\n\n  Google Forms: [link={GF}]{GF}[/link]'
                f'\n        GitHub: [link={GH}]{GH}[/link]'
                '\n\n[/][error]'
            )
