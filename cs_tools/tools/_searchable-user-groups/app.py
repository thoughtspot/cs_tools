from typing import Tuple
import pathlib
import shutil

from typer import Option as O_
import typer

from cs_tools.helpers.cli_ux import console, frontend, CSToolsGroup, CSToolsCommand
from cs_tools.util.datetime import to_datetime
from cs_tools.tools.common import run_tql_command, run_tql_script, tsload
from cs_tools.settings import TSConfig
from cs_tools.const import FMT_TSLOAD_DATETIME
from cs_tools.thoughtspot import ThoughtSpot
from cs_tools.tools import common


HERE = pathlib.Path(__file__).parent


def _get_users(api, batchsize=-1):
    """
    """
    results = []

    while True:
        n = len(results)
        r = api._metadata.list(type='USER', batchsize=batchsize, offset=n).json()
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
        n = len(results)
        r = api._metadata.list(type='USER_GROUP', batchsize=batchsize, offset=n).json()
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
    with console.status(f'getting USERS in batches of {batchsize}'):
        users  = _get_users(api, batchsize=batchsize)

    with console.status(f'getting GROUPS in batches of {batchsize}'):
        groups = _get_groups(api, batchsize=batchsize)

    asso   = []

    with console.status('associating USERS to GROUPS'):
        for group in groups:
            r = api._session.group_list_user(groupid=group['guid_']).json()

            for data in r:
                asso.append({
                    'group_guid': group['guid_'],
                    'user_guid': data['header']['id']
                })

    # HERE ALSO BE DRAGONS!
    #
    # If the platform has many tens of thousands of users or groups, it's possible that
    # this could lock up the platform.
    #
    with console.status('getting extra data on USERS and GROUPS'):
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
    Make Users and Groups searchable in your platform.

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
    cls=CSToolsGroup,
    options_metavar='[--version, --help]'
)


@app.command(cls=CSToolsCommand)
@frontend
def spotapp(
    export: pathlib.Path = O_(None, help='directory to save the spot app to', file_okay=False, resolve_path=True),
    **frontend_kw
):
    """
    Exports the SpotApp associated with this tool.
    """
    shutil.copy(HERE / 'static' / 'spotapps.zip', export)
    console.print(f'moved the SpotApp to {export}')


@app.command(cls=CSToolsCommand)
@frontend
def gather(
    export: pathlib.Path = O_(None, help='if specified, directory to save data to', file_okay=False, resolve_path=True),
    # maintained for backwards compatability
    backwards_compat: pathlib.Path = O_(None, '--save_path', help='backwards-compat if specified, directory to save data to', hidden=True),
    **frontend_kw
):
    """
    Gather and optionally, insert data into Falcon.

    By default, data is automatically gathered and inserted into the
    platform. If --export argument is used, data will not be inserted
    and will instead be dumped to the location specified.
    """
    cfg = TSConfig.from_cli_args(**frontend_kw, interactive=True)
    export = export or backwards_compat

    dir_ = cfg.temp_dir if export is None else export
    dir_.parent.mkdir(exist_ok=True)

    with ThoughtSpot(cfg) as ts:
        users, groups, asso = _get_users_in_group(ts.api)

        path = dir_ / 'introspect_user.csv'
        common.to_csv(users, fp=path, mode='a')
        console.print(f'wrote {len(users): >7,}     users    to {path}')

        path = dir_ / 'introspect_group.csv'
        common.to_csv(groups, fp=path, mode='a')
        console.print(f'wrote {len(groups): >7,}    groups    to {path}')

        path = dir_ / 'introspect_asso_user_group.csv'
        common.to_csv(asso, fp=path, mode='a')
        console.print(f'wrote {len(asso): >7,} associations to {path}')

        if export is not None:
            return

        with console.status('creating tables with remote TQL'):
            run_tql_command(ts, command='CREATE DATABASE cs_tools;')
            run_tql_script(ts, fp=HERE / 'static' / 'create_tables.tql')

        with console.status('loading data to Falcon with remote tsload'):
            for stem in ('introspect_user', 'introspect_group', 'introspect_asso_user_group'):
                path = dir_ / f'{stem}.csv'
                cycle_id = tsload(
                    ts,
                    fp=path,
                    target_database='cs_tools',
                    target_table=stem,
                    has_header_row=True
                )
                path.unlink()
                r = ts.api.ts_dataservice.load_status(cycle_id).json()
                m = ts.api.ts_dataservice._parse_tsload_status(r)
                console.print(m)
