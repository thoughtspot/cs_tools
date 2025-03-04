from __future__ import annotations

import logging

from httpx import HTTPStatusError
from rich import box
from rich.align import Align
from rich.table import Column, Table
import httpx
import typer

from cs_tools import _types, utils
from cs_tools.cli.dependencies import ThoughtSpot, depends_on
from cs_tools.cli.ux import RICH_CONSOLE, AsyncTyper

_LOG = logging.getLogger(__name__)
app = AsyncTyper(
    name="config",
    help="Tools for working with GitHub configurations. An org may only have one configuration.",
)


@app.command(name="create")
@depends_on(thoughtspot=ThoughtSpot())
def config_create(
    ctx: typer.Context,
    repository_url: str = typer.Option(..., help="The GitHub repository URL to use."),
    username: str = typer.Option(..., help="The username of a user with access to the GitHub repository."),
    access_token: str = typer.Option(..., help="A persanal access token with access to the GitHub repository."),
    commit_branch: str = typer.Option(..., help="The name of the branch to save TML to."),
    config_branch: str = typer.Option(..., help="The name of the branch to use for GUID mapping."),
    org_override: str = typer.Option(None, "--org", help="The default Org to switch to when issuing commands."),
) -> _types.ExitCode:
    """Creates a GitHub configuration for an org."""
    ts = ctx.obj.thoughtspot

    if ts.session_context.thoughtspot.is_orgs_enabled and org_override is not None:
        ts.switch_org(org_id=org_override)

    try:
        c = ts.api.vcs_git_config_create(
            org_identifier=org_override,
            repository_url=repository_url,
            username=username,
            access_token=access_token,
            enable_guid_mapping=True,
            commit_branch_name=commit_branch,
            configuration_branch_name=config_branch,
        )
        r = utils.run_sync(c)
        r.raise_for_status()

    except HTTPStatusError as e:
        if r.status_code == httpx.codes.BAD_REQUEST and "Repository already configured" in r.text:
            _LOG.warning("There is already an configuration for this environment!")
        else:
            _LOG.error(f"Could not create config for '{repository_url}', see logs for details..")
            _LOG.debug(f"Full error: {e}", exc_info=True)
        return 1

    # SHOW THE CONFIGURATIONS AS A TABLE.
    command = typer.main.get_command(app).get_command(ctx, "search")
    ctx.invoke(command, org_override=org_override)

    return 0


@app.command(name="update")
@depends_on(thoughtspot=ThoughtSpot())
def config_update(
    ctx: typer.Context,
    org_override: str = typer.Option(None, "--org", help="The default Org to switch to when issuing commands."),
    repository_url: str = typer.Option(None, help="The GitHub repository URL to use."),
    username: str = typer.Option(None, help="The username of a user with access to the GitHub repository."),
    access_token: str = typer.Option(None, help="A persanal access token with access to the GitHub repository."),
    commit_branch: str = typer.Option(None, help="The name of the branch to save TML to."),
    config_branch: str = typer.Option(None, help="The name of the branch to use for GUID mapping."),
) -> _types.ExitCode:
    """Updates a GitHub configuration for an Org."""
    ts = ctx.obj.thoughtspot

    _LOG.warning("Editing GitHub configurations via the CLI is deprecated. Visit the UI to update.")

    RICH_CONSOLE.print(
        f"\n"
        f"{ts.session_context.thoughtspot.url}/#/develop/api/rest/playgroundV2_0"
        f"?apiResourceId=http/api-endpoints/version-control/update-config",
        justify="center",
    )

    # SHOW THE CONFIGURATIONS AS A TABLE.
    command = typer.main.get_command(app).get_command(ctx, "search")
    ctx.invoke(command, org_override=org_override)

    return 0


@app.command(name="search")
@depends_on(thoughtspot=ThoughtSpot())
def config_search(
    ctx: typer.Context,
    org_override: str = typer.Option(None, "--org", help="The default Org to switch to when issuing commands."),
):
    """Searches for configurations."""
    ts = ctx.obj.thoughtspot

    if ts.session_context.thoughtspot.is_orgs_enabled and org_override is not None:
        org = ts.switch_org(org_id=org_override)

    c = ts.api.vcs_git_config_search(org_identifiers=None if org_override is None else [org["id"]])
    r = utils.run_sync(c)

    # fmt: off
    table = Table(
        "Org", Column("Repository", width=30), "Username", "Commit Branch", "Config Branch", "GUID Mapping",
        width=150, box=box.HORIZONTALS, border_style="fg-secondary",
    )
    # fmt: on

    for row in r.json():
        table.add_row(
            row["org"]["name"],
            row["repository_url"],
            row["username"],
            row["commit_branch_name"],
            row["configuration_branch_name"],
            "Yes" if row["enable_guid_mapping"] else "No",
        )

    RICH_CONSOLE.print("\n", Align.center(table), "\n")

    return 0
