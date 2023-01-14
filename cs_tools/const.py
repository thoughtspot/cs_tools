import pathlib

from rich.default_styles import DEFAULT_STYLES
from rich.theme import Theme
import typer


# remove colorization from repr styles
CONSOLE_THEME = Theme(
    {
        **{n: s.from_color() for n, s in DEFAULT_STYLES.items() if "repr" in n},
        "primary": "b medium_purple3",
        "secondary": "b green",
        "url": "b blue",
        "error": "b red",
        "hint": "b yellow",
        "arg": "b red",
        "opt": "gold3",
    }
)
PACKAGE_DIR = pathlib.Path(__file__).parent
TOOLS_DIR = PACKAGE_DIR / "cli" / "tools"

# ISO datetime format
FMT_TSLOAD_DATE = "%Y-%m-%d"
FMT_TSLOAD_TIME = "%H:%M:%S"
FMT_TSLOAD_DATETIME = f"{FMT_TSLOAD_DATE} {FMT_TSLOAD_TIME}"
FMT_TSLOAD_TRUE_FALSE = "True_False"

APP_DIR = pathlib.Path(typer.get_app_dir("cs_tools"))
APP_DIR.mkdir(parents=True, exist_ok=True)
APP_DIR.joinpath(".cache").mkdir(parents=True, exist_ok=True)

DOCS_BASE_URL = "https://thoughtspot.github.io/cs_tools/"
GH_ISSUES = "https://github.com/thoughtspot/cs_tools/issues/new/choose"
GH_SYNCER = f"{DOCS_BASE_URL}/syncer/what-is"
GDRIVE_FORM = "https://docs.google.com/forms/d/e/1FAIpQLScl-mXEL0kuZN494HbnvYxDEt3tVKOWqKVFvPkb7YL1tAzTTw/viewform"
