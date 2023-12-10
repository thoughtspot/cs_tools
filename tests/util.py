from __future__ import annotations

import re


def clean_args(command: str) -> list[str]:
    """
    Remove cs_tools variations.

    click.CliRunner doesn't expect to see the first term. We also have
    multiple names for the entrypoint.
    """
    VALID_ENTRYPOINTS = ("cs_tools", "cstools")

    for entrypoint in VALID_ENTRYPOINTS:
        if command.startswith(entrypoint):
            _, _, args_string = command.partition(entrypoint)
            break
    else:
        args_string = command

    # no input is interpreted as a single-space string
    if not args_string:
        return None

    return args_string.strip().split(" ")


def escape_ansi(line: str) -> str:
    """
    Delete ANSI sequences with a regular expression.

    click, typer, and rich all generate character sequences for formatting and
    color. Get rid of 'em for tests.

    Stolen: https://stackoverflow.com/a/38662876
    """
    ansi_escape = re.compile(r"(?:\x1B[@-_]|[\x80-\x9F])[0-?]*[ -/]*[@-~]")
    return ansi_escape.sub("", str(line))
