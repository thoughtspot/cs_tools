import pathlib

from rich.default_styles import DEFAULT_STYLES
from rich.theme import Theme
import typer


# remove colorization from repr styles
CONSOLE_THEME = Theme({
    **{n: s.from_color() for n, s in DEFAULT_STYLES.items() if 'repr' in n},
    'info'   : 'white',
    'warning': 'yellow',
    'error'  : 'bold red',
})
PACKAGE_DIR = pathlib.Path(__file__).parent
TOOLS_DIR = PACKAGE_DIR / 'cli' / 'tools'

# ISO datetime format
FMT_TSLOAD_DATE = '%Y-%m-%d'
FMT_TSLOAD_TIME = '%H:%M:%S'
FMT_TSLOAD_DATETIME = f'{FMT_TSLOAD_DATE} {FMT_TSLOAD_TIME}'
FMT_TSLOAD_TRUE_FALSE = 'True_False'

APP_DIR = pathlib.Path(typer.get_app_dir('cs_tools'))
APP_DIR.mkdir(parents=True, exist_ok=True)
