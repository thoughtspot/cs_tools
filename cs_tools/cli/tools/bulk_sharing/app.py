from __future__ import annotations

from typing import Literal
import logging
import threading
import time

from rich import console
from rich.align import Align
from textual_serve.server import Server
import typer

from cs_tools import _types, utils
from cs_tools.api import workflows
from cs_tools.cli import (
    custom_types,
    progress as px,
)
from cs_tools.cli.dependencies import ThoughtSpot, depends_on
from cs_tools.cli.input import ConfirmationListener
from cs_tools.cli.ux import AsyncTyper

from . import tui

_LOG = logging.getLogger(__name__)
app = AsyncTyper(
    name="bulk-sharing",
    help="""
    Scalably manage your table- and column-level security right in the browser.

    Setting up Column Level Security (especially on larger tables) can be time-consuming
    when done directly in the ThoughtSpot user interface. The web interface provided by
    this tool will allow you to quickly understand the current security settings for a
    given table across all columns, and as many groups as are in your platform. You may
    then set the appropriate security settings for those group-table combinations.
    """,
)


def _tick_tock(task: px.WorkTask) -> None:
    """I'm just a clock :~)"""
    while not task.finished:
        time.sleep(1)
        task.advance(step=1)


@app.command()
@depends_on(thoughtspot=ThoughtSpot())
def cls_ui(ctx: typer.Context, mode: Literal["web", "terminal"] = typer.Option("terminal")) -> _types.ExitCode:
    """Start the built-in webserver which runs the security management interface."""
    ts = ctx.obj.thoughtspot

    if mode == "web":
        server = Server(f"{tui.__file__} --config {ctx.obj.thoughtspot.config.name}")
        server.serve()
    else:
        ui = tui.ThoughtSpotSecurityApp(http=ts.api, ts_version=ts.session_context.thoughtspot.version)
        ui.run()

    return 0


@app.command()
@depends_on(thoughtspot=ThoughtSpot())
def from_tag(
    ctx: typer.Context,
    tag_name: str = typer.Option(..., "--tag", help="Case sensitive name of Tag of content to share."),
    groups: custom_types.MultipleInput = typer.Option(
        ...,
        help="Names of Groups to share to, comma separated.",
    ),
    share_mode: _types.ShareMode = typer.Option(
        ...,
        help="The level of access to give to all listed principals.",
    ),
    no_prompt: bool = typer.Option(False, "--no-prompt", help="disable the confirmation prompt"),
) -> _types.ExitCode:
    """Share content with the identified --tag."""
    ts = ctx.obj.thoughtspot

    try:
        c = workflows.metadata.fetch_one(tag_name, "TAG", http=ts.api)
        _ = utils.run_sync(c)
    except ValueError:
        raise typer.BadParameter(f"No tag found with the name '{tag_name}'") from None
    else:
        tag = _

    TOOL_TASKS = [
        px.WorkTask(id="PREPARE", description=f"Fetching objects with '{tag_name}' tag"),
        px.WorkTask(id="CONFIRM", description="Confirmation Prompt"),
        px.WorkTask(id="SHARING", description="Sharing objects"),
    ]

    with px.WorkTracker("Deleting objects", tasks=TOOL_TASKS) as tracker:
        guids_to_share: set[_types.GUID] = set()
        group_guids: set[_types.GUID] = set()

        with tracker["PREPARE"] as this_task:
            t = ["CONNECTION", "LOGICAL_TABLE", "LIVEBOARD", "ANSWER"]
            c = workflows.metadata.fetch_all(metadata_types=t, tag_identifiers=[tag["metadata_id"]], http=ts.api)
            d = utils.run_sync(c)
            guids_to_share.update(_["metadata_id"] for _ in d)

            c = utils.bounded_gather(
                *[workflows.metadata.fetch_one(identifier=g, metadata_type="USER_GROUP", http=ts.api) for g in groups],
                max_concurrent=15,
            )
            d = utils.run_sync(c)
            group_guids.update(_["metadata_id"] for _ in d)

        with tracker["CONFIRM"] as this_task:
            if no_prompt:
                this_task.skip()
            else:
                this_task.description = "[fg-warn]Confirmation prompt"
                this_task.total = ONE_MINUTE = 60

                tracker.extra_renderable = lambda: Align.center(
                    console.Group(
                        Align.center(f"{len(guids_to_share):,} objects will be shared"),
                        "\n[fg-warn]Press [fg-success]Y[/] to proceed, or [fg-error]n[/] to cancel.",
                    )
                )

                th = threading.Thread(target=_tick_tock, args=(this_task,))
                th.start()

                kb = ConfirmationListener(timeout=ONE_MINUTE)
                kb.run()

                assert kb.response is not None, "ConfirmationListener never got a response."

                tracker.extra_renderable = None
                this_task.final()

                if kb.response.upper() == "N":
                    this_task.description = "[fg-error]Denied[/] (no sharing done)"
                    return 0
                else:
                    this_task.description = f"[fg-success]Approved[/] (sharing {len(guids_to_share):,})"

        with tracker["SHARING"] as this_task:
            c = ts.api.security_metadata_share(guids=guids_to_share, principals=group_guids, share_mode=share_mode)
            _ = utils.run_sync(c)

    return 0
