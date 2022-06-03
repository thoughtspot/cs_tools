from typer import Argument as A_, Option as O_  # noqa

from cs_tools.const import APP_DIR


CONFIG_OPT = O_(
    ...,
    '--config',
    help='config file identifier',
    metavar='NAME'
)

VERBOSE_OPT = O_(
    False,
    '--verbose',
    help='enable verbose logging by default',
    hidden=True,
    show_default=False
)

TEMP_DIR_OPT = O_(
    APP_DIR,
    '--temp_dir',
    help='location on disk to save temporary files',
    file_okay=False,
    resolve_path=True,
    hidden=True,
    show_default=False,
)
