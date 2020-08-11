from typing import List, Dict, Any
import logging
import csv

from thoughtspot.util.datetime import timestamp_to_datetime
from thoughtspot.util.swagger import to_array
from thoughtspot.const import FMT_TSLOAD_DATETIME


_log = logging.getLogger(__name__)
FLAT_API_RESPONSE = List[Dict[str, Any]]


def _internal_name_lookup(name: str) -> str:
    """
    """
    mapping = {
        'QUESTION_ANSWER_BOOK': 'saved answer',
        'PINBOARD_ANSWER_BOOK': 'pinboard',
        'USER_DEFINED': 'imported table',
        'ONE_TO_ONE_LOGICAL': 'table',  # worksheet?
        'AGGR_WORKSHEET': 'view',  # worksheet?

        # what's the difference here...
        'LOGICAL_TABLE': 'worksheet',
        'WORKSHEET': 'worksheet',

        # so far unsused from Tyler's script
        'INSIGHT': 'spotiq insight',
        'PINBOARD': 'pinboard',
    }

    return mapping[name]


def _url_lookup(name: str) -> str:
    """
    """
    mapping = {
        'imported table': 'data/tables',
        'worksheet': 'data/tables',
        'table': 'data/tables',
        'view': 'data/tables',
        'spotiq insight': 'insight'
    }

    try:
        return mapping[name]
    except KeyError:
        return name.replace(' ', '-')


def _get_worksheets(api) -> FLAT_API_RESPONSE:
    """
    """
    r = api._metadata.list(type='LOGICAL_TABLE', category='ALL', showHidden=True)
    worksheets = []

    for item in r.json()['headers']:
        if item['type'] == 'CALENDAR_TABLE' or item['name'].startswith('TS:'):
            continue

        worksheets.append({
            'name': item['name'],
            'type': item['type'],
            'guid': item['id']
        })

    return worksheets


def _get_dependents(api) -> FLAT_API_RESPONSE:
    """
    """
    TS_HOST = api.config.thoughtspot.host

    worksheets = _get_worksheets(api)
    guids = map(lambda e: e['guid'], worksheets)

    r = api._dependency.list_dependents(type=None, id=to_array(guids))
    dependencies = []

    for parent_guid, info in r.json().items():
        try:
            parent = next((w for w in worksheets if w['guid'] == parent_guid))
        except StopIteration:
            _log.error(
                '>>>>> ERROR <<<<<<',
                f'\n{parent_guid}',
                f'\n{info}'
            )
            return []
        else:
            parent_type = _internal_name_lookup(parent['type'])
            parent_url = f"{TS_HOST}/#/{_url_lookup(parent_type)}/{parent['guid']}"

        # NOTE:
        #
        # this dep tree will only go 1 level deep, we might be able to sort
        # the list_dependents api response [note: r.json().items()] to allow
        # us to print the entire dependency tree linearly.
        _dependency_tree_msg = (
            f"\n{parent['name']}  <-- ({parent['type']} aka '{parent_type}')"
            f'\n  has the following dependents..'
        )

        for dependency_type, dependents in info.items():
            dependent_type = _internal_name_lookup(dependency_type)

            for dependent in dependents:
                # TODO: subclassify insights? (a type of pinboard, SpotIQ)
                #
                # if dependent_type == 'pinboard':
                #     [snipped from tyler's old scripts]
                #     if dependent['reportContent']['sheets'][0]['sheetContent']['sheetContentType'] == 'INSIGHT' ?
                #     print(dependent)
                #

                url = f"{TS_HOST}/#/{_url_lookup(dependent_type)}/{dependent['id']}"
                created = timestamp_to_datetime(dependent['created'], unit='ms')
                modified = timestamp_to_datetime(dependent['modified'], unit='ms')

                _dependency_tree_msg += (
                    f"\n  - {dependent['name']}  <-- ({dependency_type} aka "
                    f"{dependent_type})"
                )

                dependencies.append({
                    'parent_guid': parent['guid'],
                    'parent_type': parent_type,
                    'parent_name': parent['name'],
                    'parent_url': parent_url,
                    'guid': dependent['id'],
                    'type': dependent_type,
                    'name': dependent['name'],
                    'url': url,
                    'author_name': dependent['authorName'],
                    'author_display_name': dependent['authorDisplayName'],
                    'date_created': created.strftime(FMT_TSLOAD_DATETIME),
                    'date_modified': modified.strftime(FMT_TSLOAD_DATETIME)
                })\

        _log.debug(f'dependency tree:\n{_dependency_tree_msg}\n')

    return dependencies


def app(api, *, filename):
    """
    """
    with api:
        dependencies = _get_dependents(api)

    with open(filename, mode='w', encoding='utf-8', newline='') as c:
        writer = csv.DictWriter(c, dependencies[0].keys())
        writer.writeheader()
        writer.writerows(dependencies)


def parse_arguments():
    """
    """


if __name__ == '__main__':
    import argparse
    from thoughtspot.settings import TSConfig
    from thoughtspot.api import ThoughtSpot

    args = parse_arguments()
    config = TSConfig.from_toml('../../tsconfig.toml')
    ts_api = ThoughtSpot(config)

    app(ts_api, filename='./test.csv')
