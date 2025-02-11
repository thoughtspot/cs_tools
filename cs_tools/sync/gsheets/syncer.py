from __future__ import annotations

from typing import Literal
import logging
import pathlib

import gspread
import pydantic
import pydantic_core

from cs_tools import _types, errors
from cs_tools.sync import utils as sync_utils
from cs_tools.sync.base import Syncer

_LOG = logging.getLogger(__name__)


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

        try:
            self._client = gspread.service_account(filename=self.credentials_file)
            self._workbook = self._client.open(self.spreadsheet)

        except gspread.exceptions.SpreadsheetNotFound:
            raise errors.SyncerInitError(
                protocol="gsheets",
                pydantic_error=pydantic_core.ValidationError.from_exception_data(
                    title="Spreadsheet not found",
                    line_errors=[
                        pydantic_core.InitErrorDetails(
                            type="value_error",
                            loc=("spreadsheet",),
                            input=self.spreadsheet,
                            ctx={"error": ValueError(f"Spreadsheet named '{self.spreadsheet}' not found.")},
                        )
                    ],
                ),
            ) from None

        except gspread.exceptions.GSpreadException as e:
            _LOG.debug(f"{e}", exc_info=True)
            raise errors.SyncerInitError(
                protocol="gsheets",
                pydantic_error=pydantic_core.ValidationError.from_exception_data(
                    title="Spreadsheet not found",
                    line_errors=[
                        pydantic_core.InitErrorDetails(
                            type="assertion_error",
                            loc=("credentials_file",),
                            input=self.credentials_file,
                            ctx={"error": e},
                        )
                    ],
                ),
            ) from None

    @property
    def url(self) -> str:
        """Return the URL of the Google Sheet."""
        return self._workbook.url

    def tab(self, tab_name: str) -> gspread.worksheet.Worksheet:
        """Fetch the tab. If it does not yet exist, create it."""
        try:
            tab = self._workbook.worksheet(title=tab_name)
        except gspread.WorksheetNotFound:
            tab = self._workbook.add_worksheet(title=tab_name, rows=1000, cols=26)

        return tab

    def __repr__(self):
        return f"<GoogleSheetsSyncer url='{self._workbook.url}' in '{self.save_strategy}' mode>"

    # MANDATORY PROTOCOL MEMBERS

    def load(self, tab_name: str) -> _types.TableRowsFormat:
        """Read rows from a tab in the Workbook."""
        tab = self.tab(tab_name)

        if not (data := tab.get_all_records()):
            _LOG.warning(f"No data found in tab '{tab_name}'")

        return data

    def dump(self, tab_name: str, *, data: _types.TableRowsFormat) -> None:
        """Write rows to a tab in the Workbook."""
        if not data:
            _LOG.warning(f"No data to write to syncer {self}")
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
                _LOG.error(f"GoogleSheets Error: {e._extract_text(e)}")
            except AttributeError:
                _LOG.error(f"GoogleSheets Error: {e}")

            if "limit of 10000000 cells" in str(e):
                _LOG.warning("Consider using a Database Syncer instead, such as SQLite.")
