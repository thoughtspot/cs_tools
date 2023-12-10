from __future__ import annotations

import cs_tools

if __name__ == "__main__":
    import cProfile
    import pathlib
    import sys

    import snakeviz

    o = pathlib.Path("cs_tools.profile")
    p = cProfile.Profile()
    p.enable()

    try:
        cs_tools.cli.run()
    finally:
        p.disable()
        p.dump_stats(o.as_posix())

    # reset cli args to simply call snakeviz
    sys.argv = ["snakeviz", o.as_posix()]
    snakeviz.cli.main()
