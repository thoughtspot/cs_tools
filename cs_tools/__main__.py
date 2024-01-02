from __future__ import annotations

import logging

try:
    from cs_tools.cli.main import run

except ImportError:
    from cs_tools import __version__

    logging.warning(
        f"You are attempting to run cs_tools as a script (invoking cli mode), but have installed CS Tools as a package!"
        f"\n\nPlease run the command below to invoke the tools directly."
        f"\n  python -m pip install cs_tools[cli] @ https://github.com/thoughtspot/cs_tools/archive/v{__version__}.zip",
    )

else:
    run()
