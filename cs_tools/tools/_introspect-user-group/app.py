from typing import Tuple
import pathlib
import shutil

from typer import Option as O_
import typer

from cs_tools.helpers.cli_ux import console, frontend, RichGroup, RichCommand
from cs_tools.util.datetime import to_datetime
from cs_tools.tools.common import to_csv, run_tql_script, tsload
from cs_tools.settings import TSConfig
from cs_tools.const import FMT_TSLOAD_DATETIME
from cs_tools.api import ThoughtSpot


HERE = pathlib.Path(__file__).parent


def _get_users(api: ThoughtSpot, batchsize=-1):
    """
    """
    results = []

    while True:
        r = api._metadata.list(type='USER', batchsize=batchsize).json()
        results.extend([
            {
                'guid_': user['id'],
                'name': user['name'],
                'display_name': user['displayName'],
                # 'email': None,
                'created': to_datetime(user['created'], unit='ms').strftime(FMT_TSLOAD_DATETIME),
                'modified': to_datetime(user['modified'], unit='ms').strftime(FMT_TSLOAD_DATETIME),
                # 'sharing_visibility': 'sharable' if user['visibility'] == 'DEFAULT' else 'not sharable',
                'type': user['type'].split('_')[0]
            }
            for user in r['headers']
        ])

        if r['isLastBatch']:
            break

    return results


def _get_groups(api: ThoughtSpot, batchsize=-1):
    """
    """
    results = []

    while True:
        r = api._metadata.list(type='USER_GROUP', batchsize=batchsize).json()
        results.extend([
            {
                'guid_': group['id'],
                'name': group['name'],
                'display_name': group['displayName'],
                'description': group.get('description'),
                'created': to_datetime(group['created'], unit='ms').strftime(FMT_TSLOAD_DATETIME),
                'modified': to_datetime(group['modified'], unit='ms').strftime(FMT_TSLOAD_DATETIME),
                # 'sharing_visibility': 'sharable' if principal['visibility'] == 'DEFAULT' else 'not sharable',
                'type': group['type'].split('_')[0]
            }
            for group in r['headers']
        ])

        if r['isLastBatch']:
            break

    return results


def _get_users_in_group(api: ThoughtSpot, batchsize=500) -> Tuple[list, list, list]:
    """
    """
    # HERE BE DRAGONS!
    #
    # We're batching our API calls, buuuut if the platform has a large amount of groups
    # or users, like, in the thousands, then we might run into a rate limit issue when
    # making the associations.
    #
    users  = _get_users(api, batchsize=batchsize)
    groups = _get_groups(api, batchsize=batchsize)
    asso   = []

    for group in groups:
        r = api._session.group_list_user(group_id=group['guid_']).json()

        for data in r:
            asso.append({'group_guid': group['guid_'], 'user_guid': data['header']['id']})

    # HERE ALSO BE DRAGONS!
    #
    # If the platform has many tens of thousands of users or groups, it's possible that
    # this could lock up the platform.
    #
    r = api.user.list().json()

    for principal in r:
        if 'GROUP' in principal['principalTypeEnum']:
            for idx, group in enumerate(groups):
                if group['name'] != principal['name']:
                    continue

                group['sharing_visibility'] = 'sharable' if principal['visibility'] == 'DEFAULT' else 'not sharable'
                groups[idx] = group
                break

        if 'USER' in principal['principalTypeEnum']:
            for idx, user in enumerate(users):
                if user['name'] != principal['name']:
                    continue

                user['email'] = principal.get('mail')
                user['sharing_visibility'] = 'sharable' if principal['visibility'] == 'DEFAULT' else 'not sharable'
                users[idx] = user
                break

    return users, groups, asso


app = typer.Typer(
    help="""
    Make your Users and Groups searchable.

    [b][yellow]USE AT YOUR OWN RISK![/b] This tool uses private API calls which
    could change on any version update and break the tool.[/]

    Return data on your users, groups, and each users' group membership.

    \b
    Users                       Groups
    - guid                      - guid
    - email                     - description
    - name                      - name
    - display name              - display name
    - created                   - created
    - modified                  - modified
    - sharing visibility        - sharing visibility
    - user type                 - group type
    """,
    cls=RichGroup
)


@app.command(cls=RichCommand)
@frontend
def tml(
    save_path: pathlib.Path=O_(..., help='filepath to save TML files to', prompt=True),
    **frontend_kw
):
    """
    Create TML files.

    Generates and saves multiple TML files.

    \b
    TABLE:
      - introspect_user
      - introspect_group
      - introspect_asso_user_group
    """
    for file in (HERE / 'static').glob('*.tml'):
        shutil.copy(file, save_path)


@app.command(cls=RichCommand)
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
        raise typer.Exit()

    dir_ = save_path if save_path is not None else app_dir

    with ThoughtSpot(cfg) as api:
        users, groups, asso = _get_users_in_group(api)

        to_csv(users, fp=dir_ / 'introspect_user.csv')
        to_csv(groups, fp=dir_ / 'introspect_group.csv')
        to_csv(asso, fp=dir_ / 'introspect_asso_user_group.csv')

        if save_path is not None:
            return

        run_tql_script(api, fp=HERE / 'static' / 'create_tables.tql')

        for stem in ('introspect_user', 'introspect_group', 'introspect_asso_user_group'):
            path = dir_ / f'{stem}.csv'
            cycle_id = tsload(api, fp=path, target_database='cs_tools', target_table=stem)
            path.unlink()

            if cycle_id is None:
                continue

            r = api.ts_dataservice.load_status(cycle_id).json()
            m = api.ts_dataservice._parse_tsload_status(r)
            console.print(m)
