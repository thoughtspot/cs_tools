"""
Spec for `cs_tools self sync`.

Sync refreshes a few fast-moving dependencies inside an existing installation. The upgrade must be
restricted to the package being synced: an unrestricted upgrade lets the resolver move every
transitive dependency as well, which overrides the versions cs_tools pins (click, for one) and
leaves every command failing on startup.
"""

from __future__ import annotations

from cs_tools.cli.commands import self as self_commands


def test_sync_restricts_the_upgrade_to_the_named_package(monkeypatch):
    calls: list[tuple[str, tuple[str, ...]]] = []

    def record(package: str, *args: str, **_) -> None:
        calls.append((package, args))

    monkeypatch.setattr(self_commands.cs_tools_venv, "install", record)

    self_commands.sync()

    assert calls, "sync installed nothing"
    for package, args in calls:
        assert "--upgrade" not in args, f"{package}: an unrestricted upgrade moves pinned dependencies"
        assert args[:2] == ("--upgrade-package", package)
        assert "--prerelease=allow" in args
