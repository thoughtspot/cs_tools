from typing import List
import collections
import itertools as it
import logging
import json

from rich.table import Table
from typer import Argument as A_, Option as O_
import httpx
import typer

from cs_tools.cli.tools.common import setup_thoughtspot, teardown_thoughtspot
from cs_tools.cli.dependency import depends
from cs_tools.cli.options import CONFIG_OPT, VERBOSE_OPT, TEMP_DIR_OPT
from cs_tools.cli.ux import CommaSeparatedValuesType, SyncerProtocolType
from cs_tools.cli.ux import console, CSToolsGroup, CSToolsCommand
from cs_tools.thoughtspot import ThoughtSpot
from cs_tools.data.enums import GUID


log = logging.getLogger(__name__)


def _all_user_content(user: GUID, ts: ThoughtSpot):
    """
    Return all content owned by this user.
    """
    types = (
        'QUESTION_ANSWER_BOOK',
        'PINBOARD_ANSWER_BOOK',
        'LOGICAL_TABLE',
        'TAG',
        'DATA_SOURCE'
    )
    content = []

    for metadata_type in types:
        offset = 0

        while True:
            r = ts.api._metadata.list(type=metadata_type, batchsize=500, offset=offset)
            data = r.json()
            offset += len(data)

            for metadata in data['headers']:
                if metadata['author'] == user:
                    metadata['type'] = metadata_type
                    content.append(metadata)

            if data['isLastBatch']:
                break

    return content


def _get_current_security(ts: ThoughtSpot):
    """
    """
    users_and_groups = ts.api.user.list().json()
    users = []
    groups = []
    associations = []

    for principal in users_and_groups:
        data = {
            'display_name': principal['displayName'],
            'visibility': principal['visibility'],
            'type': principal['principalTypeEnum']
        }

        if 'USER' in principal['principalTypeEnum']:
            type_ = 'USER'
            users.append({
                'username': principal['name'],
                'email': principal['mail'],
                **data
            })

        if 'GROUP' in principal['principalTypeEnum']:
            type_ = 'GROUP'
            groups.append({
                'group_name': principal['name'],
                'description': principal.get('description'),
                **data
            })

        for group in principal['groupNames']:
            associations.append({
                'principal_name': principal['name'],
                'principal_type': type_,
                'group_name': group
            })

    return users, groups, associations


def _form_principals(users, groups, xref):
    principals = []
    principals_groups = collections.defaultdict(list)

    for x in xref:
        principals_groups[x['principal_name']].append(x['group_name'])

    for group in groups:
        principals.append({
            'name': group['group_name'],
            'displayName': group['display_name'],
            'description': group['description'],
            'principalTypeEnum': group['type'],
            'groupNames': principals_groups[group['group_name']],
            'visibility': group['visibility']
        })

    for user in users:
        principals.append({
            'name': user['username'],
            'displayName': user['display_name'],
            'mail': user['email'],
            'principalTypeEnum': user['type'],
            'groupNames': principals_groups[user['username']],
            'visibility': user['visibility']
        })

    return principals


app = typer.Typer(
    help="""
    Managing Users and Groups in bulk.
    """,
    cls=CSToolsGroup,
    options_metavar='[--version, --help]'
)


@app.command(cls=CSToolsCommand)
@depends(
    'thoughtspot',
    setup_thoughtspot,
    options=[CONFIG_OPT, VERBOSE_OPT, TEMP_DIR_OPT],
    teardown=teardown_thoughtspot,
)
def transfer(
    ctx: typer.Context,
    from_: str = O_(..., '--from', help='username of the current content owner'),
    to_: str = O_(..., '--to', help='username to transfer content to'),
    tag: List[str] = O_(
        None,
        callback=lambda ctx, to: CommaSeparatedValuesType().convert(to, ctx=ctx),
        help='if specified, only move content marked with one or more of these tags'
    ),
    guids: List[str] = O_(
        None,
        callback=lambda ctx, to: CommaSeparatedValuesType().convert(to, ctx=ctx),
        help='if specified, only move specific objects'
    )
):
    """
    Transfer ownership of objects from one User to another.

    Tags and GUIDs constraints are applied in OR fashion.
    """
    ts = ctx.obj.thoughtspot
    ids = set()

    if tag is not None or guids is not None:
        with console.status(f'[bold green]Getting all content by: {from_}'):
            user = ts.user.get(from_)
            content = _all_user_content(user=user['id'], ts=ts)

        if tag is not None:
            ids.update([_['id'] for _ in content if set([t['name'] for t in _['tags']]).intersection(set(tag))])

        if guids is not None:
            ids.update([_['id'] for _ in content if _['id'] in guids])

    amt = len(ids) if ids else 'all'

    with console.status(f'[bold green]Transferring {amt} objects from "{from_}" to "{to_}"'):
        try:
            r = ts.api.user.transfer_ownership(
                    fromUserName=from_,
                    toUserName=to_,
                    objectsID=ids
                )
        except Exception:
            json_msg = r.json()['debug']
            msg = json.loads(json_msg)  # uhm, lol?
            console.print(f'[red]Failed transferral of objects. {msg[-1]}')
        else:
            console.print(f'[green]Transferred {amt} objects from "{from_}" to "{to_}"')


@app.command(cls=CSToolsCommand)
@depends(
    'thoughtspot',
    setup_thoughtspot,
    options=[CONFIG_OPT, VERBOSE_OPT, TEMP_DIR_OPT],
    teardown=teardown_thoughtspot,
)
def rename(
    ctx: typer.Context,
    from_: str = O_(None, '--from', help='current username'),
    to_: str = O_(None, '--to', help='new username'),
    syncer: str = O_(
        None,
        help='protocol and path for options to pass to the syncer',
        metavar='protocol://DEFINITION.toml',
        callback=lambda ctx, to: SyncerProtocolType().convert(to, ctx=ctx)
    ),
    remapping: str = O_(
        None,
        help='if using --syncer, directive to find user remapping at'
    )
):
    """
    Remap Users from one username to another.

    If you are renaming from an external data source, your data must follow the
    tabular format below.

    \b
    +----------------+---------------------------+
    | from_username  |        to_username        |
    +----------------+---------------------------+
    | cs_tools       | cstools                   |
    | namey.namerson | namey@thoughtspot.com     |
    | fake.user      | fake.user@thoughtspot.com |
    +----------------+---------------------------+
    """
    if syncer is not None:
        if remapping is None:
            console.print('[red]you must provide a syncer directive to --remapping')
            raise typer.Exit(-1)

        remapping = {r['from_username']: r['to_username'] for r in syncer.load(remapping)}
    elif from_ is None or to_ is None:
        missing = '--from' if from_ is None else '--to'
        other = '--to' if from_ is None else '--from'
        console.print(f'if {other} is supplied, {missing} must also be given!')
        raise typer.Exit(-1)
    else:
        remapping = {from_: to_}

    ts = ctx.obj.thoughtspot

    with console.status('getting all existing users in ThoughtSpot..'):
        users = ts.user.all()

    with console.status(f'attempting update for {len(remapping)} users..'):
        for user in users:
            if user['name'] not in remapping:
                continue
            if user['name'] in ('tsadmin', 'system', 'admin', 'su'):
                console.log(f'[yellow]renaming {user["name"]} is not allowed!')
                continue

            r = ts.api.metadata.details(id=[user['id']], type='USER')

            # get existing user data
            user_data = r.json()['storables'][0]

            # update it with the new username
            user_data['header']['name'] = remapping.pop(user['name'])

            try:
                r = ts.api._session.user_update(userid=user['id'], content=user_data)
            except httpx.HTTPStatusError:
                console.print(f'rename [red]failed[/] for [yellow]{from_}[/]')
            else:
                console.print(f'rename [green]complete[/]: [yellow]{from_} [white]-->[/] {to_}')

    if remapping:
        not_renamed = '\n  - '.join(remapping)
        console.print(f'\n[yellow]users not found in system:[/]\n  - {not_renamed}')


@app.command(cls=CSToolsCommand)
@depends(
    'thoughtspot',
    setup_thoughtspot,
    options=[CONFIG_OPT, VERBOSE_OPT, TEMP_DIR_OPT],
    teardown=teardown_thoughtspot,
)
def sync(
    ctx: typer.Context,
    # Note:
    # really this is a SyncerProtocolType type,
    # but typer does not yet support click.ParamType,
    # so we can fake it with a callback :~)
    syncer: str = A_(
        ...,
        help='protocol and path for options to pass to the syncer',
        metavar='protocol://DEFINITION.toml',
        callback=lambda ctx, to: SyncerProtocolType().convert(to, ctx=ctx)
    ),
    users: str = O_('ts_auth_sync_users', help='directive to find users to sync at'),
    groups: str = O_('ts_auth_sync_groups', help='directive to find groups to sync at'),
    associations: str = O_('ts_auth_sync_xref', help='directive to find associations to sync at'),
    apply_changes: bool = O_(
        False,
        '--apply-changes',
        help='whether or not to sync the security strategy into ThoughtSpot',
        show_default=False,
    ),
    new_user_password: str = O_(
        None,
        help='password for new users added during the sync operation',
    ),
    dont_remove_deleted: bool = O_(
        True,
        help='whether to remove the deleted users and user groups',
        show_default=False
    ),
    export: bool = O_(
        False,
        '--export',
        help='whether or not to dump data to the syncer',
        show_default=False
    ),
):
    """
    Sync your Users and Groups from an external data source.

    \b
    During this operation, Users and Groups..
    - present in ThoughtSpot, but not present in Syncer are [red]deleted[/] in ThoughtSpot
      - if using the --no-remove-deleted flag, users will not be deleted in this case
    - not present in ThoughtSpot, but present in Syncer are [green]created[/] in ThoughtSpot
    - present in ThoughtSpot, and in Syncer are [yellow]updated[/] by their attributes
      - this includes group membership
    """
    ts = ctx.obj.thoughtspot

    if export:
        with console.status('[bold green]getting existing security strategy..'):
            u, g, x = _get_current_security(ts)

        with console.status(f'[bold green]writing security strategy to {syncer.name}..'):
            syncer.dump(users, data=u)
            syncer.dump(groups, data=g)
            syncer.dump(associations, data=x)
        raise typer.Exit()

    with console.status(f'[bold green]loading security strategy from {syncer.name}..'):
        u = syncer.load(users)
        g = syncer.load(groups)
        x = syncer.load(associations)

    with console.status('[bold green]syncing security strategy to [white]ThoughtSpot[/]..'):
        principals = _form_principals(u, g, x)

        r = ts.api.user.sync(
                principals=principals,
                applyChanges=False,
                removeDeleted=dont_remove_deleted,
                password=new_user_password
            )

        d = r.json()
        log.debug(d)

        # draw the tables
        for principal in ('users', 'groups'):
            a = d[f'{principal}Added']
            u = d[f'{principal}Updated']
            r = d[f'{principal}Deleted']
            t = Table(
                    'added', 'updated', 'removed',
                    title=f'Synced {principal}'.title(),
                    caption=f'{len(a) + len(u) + len(r)} {principal} synced'
                )

            for row in it.zip_longest(a, u, r):
                t.add_row(*row)

            console.log('\n', t, justify='center')
            console.print('\n\n')
