"""
Behavioral spec for the CLI's process exit code.

CI pipelines gate on cs_tools' exit code (see docs/guides/process-vcs.md). The console-script
exe wraps the entrypoint in sys.exit(run()), but `python -m cs_tools` executes __main__.py --
which once called run() WITHOUT sys.exit, discarding every command's return code and exiting 0.
A pipeline invoking cs_tools that way treats every failure as success.
"""

from __future__ import annotations

import os
import subprocess
import sys


def test_python_dash_m_propagates_the_command_exit_code(tmp_path):
    # A MISSING CONFIG IS A DETERMINISTIC, NO-NETWORK FAILURE: CSToolsError -> run() RETURNS 1.
    # POINTING THE CS TOOLS HOME AT tmp_path GUARANTEES THE CONFIG IS MISSING AND KEEPS THE
    # RUN'S LOGFILE OUT OF THE REAL USER DIRECTORY (WINDOWS READS APPDATA, LINUX XDG).
    env = {**os.environ, "APPDATA": str(tmp_path), "XDG_CONFIG_HOME": str(tmp_path)}

    proc = subprocess.run(
        [sys.executable, "-m", "cs_tools", "config", "check", "--config", "definitely-not-a-real-config"],
        env=env,
        capture_output=True,
        timeout=60,
    )

    assert proc.returncode == 1, proc.stdout
