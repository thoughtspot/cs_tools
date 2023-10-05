from typing import Union

import typer

from cs_tools.cli.dependencies import thoughtspot
from cs_tools.cli.types import MultipleChoiceType
from cs_tools.cli.ux import CSToolsApp, rich_console
from cs_tools.types import GUID

Identifier = Union[GUID, int, str]

app = CSToolsApp(
    name="config",
    help="Tools for working with git configurations.",
    add_completion=False,
    invoke_without_command=True,
    no_args_is_help=True,
)


@app.command(dependencies=[thoughtspot], name="create")
def config_create(
        ctx: typer.Context,
        repository: str = typer.Option(None, help="the git repository to use"),
        username: str = typer.Option(None, help="the username to use for the git repository"),
        access_token: str = typer.Option(None, help="the access token to use for the git repository"),
        org: str = typer.Option(None, help="the org to use if any"),
        branch_names: str = typer.Option(None,
                                         custom_type=MultipleChoiceType(),
                                         help="the branch names to use for the git repository"),
        default_branch_name: str = typer.Option(None, help="the default branch name to use for the git repository"),
        enable_guid_mapping: bool = typer.Option(False, help="the enable guid mapping to use for the git repository"),
        guid_mapping_branch_name: str = typer.Option(None,
                                                     help="the guid mapping branch name to use for the git repository"),
):
    """
    Creates a configuration for a cluster or org.  An org can only have a single configuration.
    """
    ts = ctx.obj.thoughtspot

    # check for required parameters
    if repository is None or username is None or access_token is None:
        rich_console.print("[bold red]Must minimally provide the repository, username, and access_token.[/]")
        return

    if org is not None:
        ts.org.switch(org)

    r = ts.api_v2.vcs_git_config_create(
        repository_url=repository,
        username=username,
        access_token=access_token,
        org_identifier=org,
        branch_names=branch_names,
        default_branch_name=default_branch_name,
        enable_guid_mapping=enable_guid_mapping,
        guid_mapping_branch_name=guid_mapping_branch_name
    )

    if not r.is_success:
        rich_console.print(f"[bold red]Error creating the configuration: {r}.[/]")
        rich_console.print(f"[bold red]{r.content}.[/]")
    else:
        rich_console.print(r.json())


@app.command(dependencies=[thoughtspot], name="update")
def config_update(
        ctx: typer.Context,
        repository: str = typer.Argument(..., help="the git repository to use"),
        username: str = typer.Argument(..., help="the username to use for the git repository"),
        access_token: str = typer.Argument(..., help="the access token to use for the git repository"),
        org: str = typer.Option(None, help="the org to update the configuration for"),
        branch_names: str = typer.Option(None,
                                         custom_type=MultipleChoiceType(),
                                         help="the branch names to use for the git repository"),
        default_branch_name: str = typer.Option(None, help="the default branch name to use for the git repository"),
        enable_guid_mapping: bool = typer.Option(False, help="the enable guid mapping to use for the git repository"),
        guid_mapping_branch_name: str = typer.Option(None,
                                                     help="the guid mapping branch name to use for the git repository"),
):
    """
    Updates a configuration for a cluster or org.
    """
    ts = ctx.obj.thoughtspot

    if org is not None:
        ts.org.switch(org)

    r = ts.api_v2.vcs_git_config_update(
        repository_url=repository,
        username=username,
        access_token=access_token,
        org_identifier=org,
        branch_names=branch_names,
        default_branch_name=default_branch_name,
        enable_guid_mapping=enable_guid_mapping,
        guid_mapping_branch_name=guid_mapping_branch_name
    )

    rich_console.print(r.json())


@app.command(dependencies=[thoughtspot], name="search")
def config_search(
        ctx: typer.Context,
        org_ids: str = typer.Argument(..., custom_type=MultipleChoiceType(),
                                      help="The org IDs to get the configuration for")
):
    """
    Searches for configurations.
    """
    ts = ctx.obj.thoughtspot

    r = ts.api_v2.vcs_git_config_search(
        org_ids=org_ids
    )

    rich_console.print(r.json())


@app.command(dependencies=[thoughtspot], name="delete")
def config_delete(
        ctx: typer.Context,
        org: str = typer.Option(None, help="the org id to delete from"),
        cluster_level: bool = typer.Option(False, help="the cluster level to use for the git repository"),
):
    """
    Deletes a configuration for a cluster or org.
    """
    ts = ctx.obj.thoughtspot

    if org is not None:
        ts.org.switch(org)
    else:
        # DEV NOTE: delete doesn't take an org, so it will use whatever the last one was.
        # It might be prudent to prompt to user if they want to continue.  It won't apply to
        # non-org enabled clusters.
        rich_console.print("[bold yellow]No org specified, the config in the current org will be deleted.[/]")

    r = ts.api_v2.vcs_git_config_delete(
        cluster_level=cluster_level
    )

    if not r.is_success:
        rich_console.print(f"[bold red]Error deleting the configuration: {r}.[/]")
        rich_console.print(f"[bold red]{r.content}.[/]")
    else:
        rich_console.print(r.json())
