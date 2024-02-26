from __future__ import annotations

import logging

try:
    from cs_tools.cli.commands.main import run

except (ModuleNotFoundError, ImportError):
    from cs_tools import __version__

    logging.warning(
        f"Unsupported mode encountered."
        f"\n\nYou are attempting to invoke the cs_tools command line, but have installed CS Tools as a package!"
        f"\n\nPlease run the command below to invoke the tools directly."
        f"\n\tpython -m pip install cs_tools[cli] @ https://github.com/thoughtspot/cs_tools/archive/v{__version__}.zip",
    )

else:
    run()
