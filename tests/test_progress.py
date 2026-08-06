"""
Spec for WorkTask phase logging.

Every phase (a `with tracker[...]:` block) emits a start line and a timed end line, so a run
narrates itself to the console and the persistent log — no more black-box phases.
"""

from __future__ import annotations

import io
import logging

from cs_tools.cli.progress import WorkTask, WorkTracker
from cs_tools.cli.ux import CS_TOOLS_THEME
from rich.console import Console


def test_phase_logs_start_and_timed_end(caplog):
    with caplog.at_level(logging.INFO):
        with WorkTask(id="TS_ORG", description="  Fetching [fg-secondary]ORG[/] data"):
            pass

    # rich markup and indentation are stripped; both start and timed-end are logged
    assert "→ Fetching ORG data" in caplog.text
    assert "✓ Fetching ORG data (" in caplog.text


def test_reentry_logs_per_entry_duration_not_cumulative(caplog):
    # The metadata command re-enters the same task once per org. Each entry must log ITS OWN
    # duration, not the accumulated total (which is what self.elapsed carries).
    task = WorkTask(id="TS_ORG", description="Fetching ORG data")
    clock = iter([0.0, 10.0, 100.0, 105.0, 200.0, 300.0])  # entry1: 0->10 (10s); entry2: 100->105 (5s)
    task.get_time = lambda: next(clock)

    with caplog.at_level(logging.INFO):
        with task:
            pass
        with task:
            pass

    assert "(10.0s)" in caplog.text  # first entry
    assert "(5.0s)" in caplog.text  # second entry, per-entry
    assert "(15.0s)" not in caplog.text  # NOT the cumulative 10 + 5


def test_phase_logs_failure_on_exception(caplog):
    with caplog.at_level(logging.INFO):
        try:
            with WorkTask(id="TS_ORG", description="Fetching ORG data"):
                raise ValueError("boom")
        except ValueError:
            pass

    assert "✗ Fetching ORG data failed after" in caplog.text
    assert "✓ Fetching ORG data" not in caplog.text


def _render_bar_cell(task: WorkTask) -> str:
    console = Console(width=120, file=io.StringIO(), theme=CS_TOOLS_THEME)
    console.print(task.__render__(text_width=40, bar_width=60))
    return console.file.getvalue()  # type: ignore[attr-defined]


def test_a_skipped_task_says_so_instead_of_dashes(caplog):
    # A DELIBERATELY SKIPPED PHASE (eg. THE TRUNCATE GUARD REFUSING AN INCOMPLETE LOAD) USED TO
    # RENDER "--", IDENTICAL TO A PHASE THAT NEVER RAN -- THE FINAL FRAME COULDN'T TELL THE USER
    # THAT DATA WAS NOT WRITTEN.
    task = WorkTask(id="DUMP_DATA", description="Sending data to snowflake")

    with caplog.at_level(logging.INFO):
        task.skip(reason="incomplete extract")

    rendered = _render_bar_cell(task)
    assert "skipped" in rendered
    assert "incomplete extract" in rendered

    # THE LOGFILE TELLS THE SAME STORY AS THE LIVE TABLE.
    assert "⤼ Sending data to snowflake skipped (incomplete extract)" in caplog.text


def test_a_never_started_task_still_renders_dashes():
    # "--" NOW MEANS EXACTLY ONE THING: THE PHASE WAS NEVER REACHED.
    task = WorkTask(id="DUMP_DATA", description="Sending data to snowflake")

    rendered = _render_bar_cell(task)
    assert "--" in rendered
    assert "skipped" not in rendered


def test_worktracker_restores_cursor_on_exit():
    # WorkTracker (rich Live) hides the cursor on enter; it MUST restore it on exit, or the cursor
    # stays hidden after the command finishes -- invisible on lenient terminals, but it persists in
    # strict emulators like cloud shells.
    console = Console(force_terminal=True, theme=CS_TOOLS_THEME, file=io.StringIO())
    calls: list[bool] = []
    real_show_cursor = console.show_cursor

    def spy(show: bool = True) -> bool:
        calls.append(show)
        return real_show_cursor(show)

    console.show_cursor = spy  # type: ignore[method-assign]

    with WorkTracker("deploy", tasks=[WorkTask(id="A", description="Fetching X")], console=console):
        pass

    # hidden on enter (False), restored on exit (True) -- the LAST toggle must be a restore
    assert calls, "cursor visibility was never toggled"
    assert calls[-1] is True, f"cursor not restored on exit; show_cursor calls={calls}"
