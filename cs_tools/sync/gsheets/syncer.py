from typing import Any, Dict, List
import logging
import pathlib
import enum

from pydantic.dataclasses import dataclass
import gspread

from .const import GOOGLE_SHEET_DEFAULT_SIZE
from . import sanitize


log = logging.getLogger(__name__)


class InsertMode(enum.Enum):
    append = 'APPEND'
    overwrite = 'OVERWRITE'


@dataclass
class GoogleSheets:
    """
    Interact with Google Sheets.

    To access spreadsheets, you'll need to authenticate first
      https://docs.gspread.org/en/latest/oauth2.html

    Parameters
    ----------
    spreadsheet: str
      name of the google sheet to interact with

    has_header_row: bool, default True
      whether or not tabs include a header row

    mode: str, default 'overwrite'
      either "append" or "overwrite"

    credentials_file: pathlib.Path, default gspread.auth.DEFAULT_SERVICE_ACCOUNT_FILENAME
      absolute path to your credentials file
    """
    spreadsheet: str
    has_header_row: bool = True
    mode: InsertMode = InsertMode.overwrite
    credentials_file: pathlib.Path = gspread.auth.DEFAULT_SERVICE_ACCOUNT_FILENAME

    def __post_init_post_parse__(self):
        self.client = gspread.service_account(filename=self.credentials_file)
        self.ws = self.client.open(self.spreadsheet)

    def _get_or_create_tab(self, tab_name: str) -> gspread.worksheet.Worksheet:
        try:
            t = self.ws.worksheet(tab_name)
        except gspread.WorksheetNotFound:
            t = self.ws.add_worksheet(tab_name, *GOOGLE_SHEET_DEFAULT_SIZE)

        return t

    def __repr__(self):
        return f"<GoogleSheet sync: worksheet='{self.ws.title}', id={self.ws.id}'>"

    # MANDATORY PROTOCOL MEMBERS

    @property
    def name(self) -> str:
        return 'gsheets'

    def load(self, tab_name: str) -> List[Dict[str, Any]]:
        t = self._get_or_create_tab(tab_name)
        data = t.get_all_records()

        if not data:
            log.warning(f"no data found in tab '{tab_name}'!")

        return data

    def dump(self, tab_name: str, *, data: List[Dict[str, Any]]) -> None:
        t = self._get_or_create_tab(tab_name)

        if self.has_header_row and not t.get('A1'):
            t.append_row(list(data[0].keys()))

        if self.mode == InsertMode.overwrite:
            beg = gspread.utils.rowcol_to_a1(2 if self.has_header_row else 1, 1)
            end = gspread.utils.rowcol_to_a1(t.row_count, t.col_count)
            t.batch_clear([f'{beg}:{end}'])

        d = sanitize.clean_for_gsheets(data)
        t.append_rows(d)
