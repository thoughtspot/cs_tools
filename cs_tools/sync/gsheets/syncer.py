from __future__ import annotations

from typing import TYPE_CHECKING, Literal
import logging
import pathlib

import gspread
import pydantic

from cs_tools.sync import utils as sync_utils
from cs_tools.sync.base import Syncer

from cs_tools import _types

log = logging.getLogger(__name__)


class GoogleSheets(Syncer):
    """Interact with a GoogleSheet."""

    __manifest_path__ = pathlib.Path(__file__).parent / "MANIFEST.json"
    __syncer_name__ = "sheets"

    spreadsheet: str
    credentials_file: pydantic.FilePath
    date_time_format: str = sync_utils.DATETIME_FORMAT_ISO_8601
    save_strategy: Literal["APPEND", "OVERWRITE"] = "OVERWRITE"

    def __init__(self, **data):
        super().__init__(**data)
        self.client = gspread.service_account(filename=self.credentials_file)
        self.workbook = self.client.open(self.spreadsheet)

    @property
    def url(self) -> str:
        """Return the URL of the Google Sheet."""
        return self.workbook.url

    def tab(self, tab_name: str) -> gspread.worksheet.Worksheet:
        """Fetch the tab. If it does not yet exist, create it."""
        try:
            tab = self.workbook.worksheet(title=tab_name)
        except gspread.WorksheetNotFound:
            tab = self.workbook.add_worksheet(title=tab_name, rows=1000, cols=26)

        return tab

    def __repr__(self):
        return f"<GoogleSheetsSyncer url='{self.workbook.url}' in '{self.save_strategy}' mode>"

    # MANDATORY PROTOCOL MEMBERS

    def load(self, tab_name: str) -> _types.TableRowsFormat:
        """Read rows from a tab in the Workbook."""
        tab = self.tab(tab_name)

        if not (data := tab.get_all_records()):
            log.warning(f"No data found in tab '{tab_name}'")

        return data

    def dump(self, tab_name: str, *, data: _types.TableRowsFormat) -> None:
        """Write rows to a tab in the Workbook."""
        if not data:
            log.warning(f"No data to write to syncer {self}")
            return

        tab = self.tab(tab_name)
        new = []

        if self.save_strategy == "OVERWRITE":
            tab.clear()

            # HEADER
            new.append(list(data[0].keys()))

        # DATA
        for row in data:
            row = sync_utils.format_datetime_values(row, dt_format=self.date_time_format)
            new.append(list(row.values()))

        # SAVE ON API CALLS, ONLY MAKE A SINGLE ONE
        try:
            tab.append_rows(new)
        except gspread.exceptions.APIError as e:
            try:
                log.error(f"GoogleSheets Error: {e._extract_text(e)}")
            except AttributeError:
                log.error(f"GoogleSheets Error: {e}")

            if "limit of 10000000 cells" in str(e):
                log.warning("Consider using a Database Syncer instead, such as SQLite.")
