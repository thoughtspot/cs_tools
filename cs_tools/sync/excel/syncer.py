from __future__ import annotations

from typing import TYPE_CHECKING, Literal, Union
import logging
import pathlib

import openpyxl
import pydantic

from cs_tools.sync import utils as sync_utils
from cs_tools.sync.base import Syncer

if TYPE_CHECKING:
    from cs_tools.sync.types import TableRows

log = logging.getLogger(__name__)


class Excel(Syncer):
    """Interact with an Excel workbook."""

    __manifest_path__ = pathlib.Path(__file__).parent / "MANIFEST.json"
    __syncer_name__ = "excel"

    filepath: Union[pydantic.FilePath, pydantic.NewPath]
    date_time_format: str = sync_utils.DATETIME_FORMAT_ISO_8601
    save_strategy: Literal["APPEND", "OVERWRITE"] = "OVERWRITE"

    def __init__(self, **data):
        super().__init__(**data)
        self.workbook = self._load_workbook()

    def _load_workbook(self) -> openpyxl.Workbook:
        try:
            wb = openpyxl.load_workbook(self.filepath)
        except FileNotFoundError:
            wb = openpyxl.Workbook()
            wb.remove(wb.active)

        return wb

    def tab(self, tab_name: str) -> openpyxl.worksheet.worksheet.Worksheet:
        """Fetch the tab. If it does not yet exist, create it."""
        try:
            tab = self.workbook[tab_name]
        except KeyError:
            tab = self.workbook.create_sheet(tab_name)

        return tab

    def __repr__(self):
        return f"<ExcelSyncer path='{self.filepath}' in '{self.save_strategy}' mode>"

    # MANDATORY PROTOCOL MEMBERS

    def load(self, tab_name: str) -> TableRows:
        """Read rows from a tab in the Workbook."""
        tab = self.tab(tab_name)

        if tab.calculate_dimension() == "A1:A1":
            log.warning(f"No data found in tab '{tab_name}'")
            return []

        header = tab.iter_rows(min_row=1, max_row=1, values_only=True)
        data = [dict(zip(header, row)) for row in tab.iter_rows(min_row=2, values_only=True)]

        if not data:
            log.warning(f"No data found in tab '{tab_name}'")

        return data

    def dump(self, tab_name: str, *, data: TableRows) -> None:
        """Write rows to a tab in the Workbook."""
        if not data:
            log.warning(f"No data to write to syncer {self}")
            return

        tab = self.tab(tab_name)

        if self.save_strategy == "OVERWRITE":
            # idx = 1 means we should delete the header as well, mostly so we can ensure
            # nothing weird happens here with data/table quality.
            tab.delete_rows(idx=1, amount=tab.max_row + 1)

            # HEADER
            tab.append(list(data[0].keys()))

        # DATA
        for row in data:
            row = sync_utils.format_datetime_values(row, dt_format=self.date_time_format)
            tab.append(list(row.values()))

        self.workbook.save(self.filepath)
