from typer import Argument as A_, Option as O_  # noqa


CONFIG_OPT = O_(
    ...,
    '--config',
    help='identifier for your thoughtspot configuration file',
    metavar='IDENTIFIER'
)

PASSWORD_OPT = O_(
    None,
    '--password',
    help='...',
    hidden=True,
    show_default=False
)

VERBOSE_OPT = O_(
    False,
    '--verbose',
    help='...',
    hidden=True,
    show_default=False
)
