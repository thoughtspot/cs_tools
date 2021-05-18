from typing import Tuple
import pathlib
import shutil

from typer import Option as O_
import typer

from cs_tools.helpers.cli_ux import console, show_tool_options, frontend
from cs_tools.util.datetime import to_datetime
from cs_tools.tools.common import to_csv, run_tql_script, tsload
from cs_tools.settings import TSConfig
from cs_tools.const import FMT_TSLOAD_DATETIME
from cs_tools.api import ThoughtSpot


HERE = pathlib.Path(__file__).parent


def _user_groups_info(api: ThoughtSpot) -> Tuple[list, list]:
    """
    """
    r = api.user.list()
    groups = []
    users = []

    for principal in r.json():
        if 'GROUP' in principal['principalTypeEnum']:
            groups.append({
                'name': principal['name'],
                'display_name': principal['displayName'],
                'description': principal.get('description', ''),
                'created': to_datetime(principal['created'], unit='ms').strftime(FMT_TSLOAD_DATETIME),
                'modified': to_datetime(principal['modified'], unit='ms').strftime(FMT_TSLOAD_DATETIME)
            })

        if 'USER' in principal['principalTypeEnum']:
            for group in principal['groupNames']:
                users.append({
                    'name': principal['name'],
                    'display_name': principal['displayName'],
                    'email': principal['mail'],
                    'group': group,
                    'created': to_datetime(principal['created'], unit='ms').strftime(FMT_TSLOAD_DATETIME),
                    'modified': to_datetime(principal['modified'], unit='ms').strftime(FMT_TSLOAD_DATETIME)
                })

    return users, groups


app = typer.Typer(
    help="""
    Gather data on your existing Users and Groups.

    Long description.
    """,
    callback=show_tool_options,
    invoke_without_command=True
)


@app.command()
@frontend
def tml(
    save_path: pathlib.Path=O_(..., help='filepath to save TML files to', prompt=True),
    **frontend_kw
):
    """
    Create TML files.

    Generates and saves multiple TML files.

    TABLE ...... introspect_user, introspect_group, introspect_asso_user_group
    """
    for file in pathlib.Path(HERE).glob('*.tml'):
        shutil.copy(file, save_path)


@app.command()
@frontend
def gather(
    save_path: pathlib.Path=O_(None, help='if specified, directory to save data to'),
    **frontend_kw
):
    """
    Gather and optionally, insert data into Falcon.

    By default, data is automatically gathered and inserted into the
    platform. If save_path argument is used, data will not be inserted
    and will instead be dumped to the location specified.
    """
    app_dir = pathlib.Path(typer.get_app_dir('cs_tools'))
    cfg = TSConfig.from_cli_args(**frontend_kw, interactive=True)

    if save_path is not None and (not save_path.exists() or save_path.is_file()):
        console.print(f'[red]"{save_path.resolve()}" should be a valid directory![/]')

    dir_ = save_path if save_path is not None else app_dir

    with ThoughtSpot(cfg) as api:
        users_, groups = _user_groups_info(api)
        seen_ = []
        users = []

        for user in users_:
            if user['name'] not in seen_:
                seen_.append(user['name'])
                users.append({k: v for k, v in user.items() if k != 'group'})

        asso  = [{'user_name': u['name'], 'group_name': u['group']} for u in users_]

        to_csv(users, fp=dir_ / 'introspect_user.csv')
        to_csv(groups, fp=dir_ / 'introspect_group.csv')
        to_csv(asso, fp=dir_ / 'introspect_asso_user_group.csv')

        if save_path is not None:
            return

        run_tql_script(api, fp=HERE / 'create_tables.tql')

        for stem in ('introspect_user', 'introspect_group', 'introspect_asso_user_group'):
            path = dir_ / f'{stem}.csv'
            cycle_id = tsload(api, fp=path, target_database='cs_tools', target_table=stem)
            path.unlink()

            if cycle_id is None:
                continue

            r = api.ts_dataservice.load_status(cycle_id)
            data = r.json()

            console.print(
                f'\nCycle ID: {data["cycle_id"]}'
                f'\nStage: {data["internal_stage"]}'
                f'\nRows written: {data["rows_written"]}'
                f'\nIgnored rows: {data["ignored_row_count"]}'
            )
