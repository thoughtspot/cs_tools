from typing import Any, Dict, List, Union
from io import BufferedIOBase
from tempfile import _TemporaryFileWrapper
import logging

from pydantic import validate_arguments

from cs_tools.data.enums import Privilege
from cs_tools.errors import InsufficientPrivileges, TSLoadServiceUnreachable
from cs_tools.const import (
    FMT_TSLOAD_DATETIME, FMT_TSLOAD_DATE, FMT_TSLOAD_TIME, FMT_TSLOAD_TRUE_FALSE
)


log = logging.getLogger(__name__)
REQUIRED_PRIVILEGES = set([
    Privilege.can_administer_thoughtspot,
    Privilege.can_manage_data
])


class TSLoadMiddleware:
    """
    """
    def __init__(self, ts):
        self.ts = ts

    def _check_privileges(self) -> None:
        """
        """
        if not set(self.ts.me.privileges).intersection(REQUIRED_PRIVILEGES):
            raise InsufficientPrivileges(
                user=self.ts.me,
                service='remote TQL',
                required_privileges=REQUIRED_PRIVILEGES
            )

    @validate_arguments(config=dict(arbitrary_types_allowed=True))
    def upload(
        self,
        fd: Union[BufferedIOBase, _TemporaryFileWrapper],
        *,
        database: str,
        table: str,
        schema_: str = 'falcon_default_schema',
        empty_target: bool = True,
        max_ignored_rows: int = 0,
        date_format: str = FMT_TSLOAD_DATE,
        date_time_format: str = FMT_TSLOAD_DATETIME,
        time_format: str = FMT_TSLOAD_TIME,
        skip_second_fraction: bool = False,
        field_separator: str = '|',
        null_value: str = '',
        boolean_representation: str = FMT_TSLOAD_TRUE_FALSE,
        has_header_row: bool = False,
        escape_character: str = '"',
        enclosing_character: str = '"',
        flexible: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Load a file via tsload on a remote server.

        Defaults to tsload command of:
            tsload --source_file <fp>
                   --target_database <target_database>
                   --target_schema 'falcon_default_schema'
                   --target_table <target_table>
                   --max_ignored_rows 0
                   --date_time_format '%Y-%m-%d %H:%M:%S'
                   --field_separator '|'
                   --null_value ''
                   --boolean_representation True_False
                   --escape_character '"'
                   --enclosing_character '"'
                   --empty_target

        For further information on tsload, please refer to:
          https://docs.thoughtspot.com/latest/admin/loading/load-with-tsload.html
          https://docs.thoughtspot.com/latest/reference/tsload-service-api-ref.html
          https://docs.thoughtspot.com/latest/reference/data-importer-ref.html

        Parameters
        ----------
        fp : pathlib.Path
          file to load to thoughtspot

        Returns
        -------
        cycle_id
          unique identifier for this specific file load

        Raises
        ------
        TSLoadServiceUnreachable
          raised when the tsload api service is not reachable
        """
        self._check_privileges()

        flags = {
            'target': {
                'database': database,
                'schema': schema_,
                'table': table
            },
            'format': {
                'field_separator': field_separator,
                'enclosing_character': enclosing_character,
                'escape_character': escape_character,
                'null_value': null_value,
                'date_time': {
                    'date_time_format': date_time_format,
                    'date_format': date_format,
                    'time_format': time_format,
                    'skip_second_fraction': skip_second_fraction
                },
                'boolean': {
                    'true_format': boolean_representation.split('_')[0],
                    'false_format': boolean_representation.split('_')[1]
                },
                'has_header_row': has_header_row,
                'flexible': flexible
            },
            'load_options': {
                'empty_target': empty_target,
                'max_ignored_rows': max_ignored_rows
            }
        }

        try:
            r = self.ts.api.ts_dataservice.load_init(flags)
        except Exception as e:
            raise TSLoadServiceUnreachable(
                f'[red]something went wrong trying to access tsload service: {e}[/]'
                f'\n\nIf you haven\'t enabled tsload service yet, please find the link '
                f'below further information:'
                f'\nhttps://docs.thoughtspot.com/latest/admin/loading/load-with-tsload.html'
                f'\n\nHeres the tsload command for the file you tried to load:'
                f'\n\ntsload --source_file {fd.name} --target_database {database} '
                f'--target_schema {schema_} --target_table {table} '
                f'--max_ignored_rows {max_ignored_rows} --date_format "{FMT_TSLOAD_DATE}" '
                f'--time_format "{FMT_TSLOAD_TIME}" --date_time_format "{FMT_TSLOAD_DATETIME}" '
                f'--field_separator "{field_separator}" --null_value "{null_value}" '
                f'--boolean_representation {boolean_representation} '
                f'--escape_character "{escape_character}" --enclosing_character "{enclosing_character}"'
                + ('--empty_target ' if empty_target else '--noempty_target ')
                + ('--has_header_row ' if has_header_row else '')
                + ('--skip_second_fraction ' if skip_second_fraction else '')
                + ('--flexible' if flexible else ''),
                http_error=e
            )

        cycle_id = r.json()['cycle_id']
        self.ts.api.ts_dataservice.load_start(cycle_id, fd=fd)
        self.ts.api.ts_dataservice.load_commit(cycle_id)
        return cycle_id

    # @validate_arguments
    # def status(self, cycle_id: str, *, wait_for_complete: bool = False):
    #     """
    #     """
    #     self._check_privileges()

    #     while True:
    #         r = self.ts.api.ts_dataservice.load_status(cycle_id)
    #         data = r.json()

    #         if not wait_for_complete:
    #             break

    #         print(data)
    #         raise

    # @validate_arguments
    # def bad_records(self, cycle_id: str) -> List[Dict[str, Any]]:
    #     """
    #     """
    #     r = self.ts.api.ts_dataservice.load_params(cycle_id)
    #     params = r.json()
    #     print(params)
    #     raise

    #     r = self.ts.api.ts_dataservice.bad_records(cycle_id)
    #     r.text
