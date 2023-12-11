from __future__ import annotations

from typing import Any
import enum
import logging
import pathlib

from pydantic.dataclasses import dataclass
import openpyxl

from . import sanitize

log = logging.getLogger(__name__)


class InsertMode(enum.Enum):
    append = "APPEND"
    overwrite = "OVERWRITE"


@dataclass
class Excel:
    """
    Interact with Excel.
    """

    filepath: pathlib.Path
    mode: InsertMode = InsertMode.overwrite

    def __post_init_post_parse__(self):
        try:
            self.wb = openpyxl.load_workbook(self.filepath)
        except FileNotFoundError:
            self.wb = openpyxl.Workbook()
            self.wb.remove(self.wb.active)

    def _get_or_create_tab(self, tab_name: str) -> openpyxl.worksheet.worksheet.Worksheet:
        try:
            t = self.wb[tab_name]
        except KeyError:
            t = self.wb.create_sheet(tab_name)

        return t

    def __repr__(self):
        return f"<ExcelWorkbook sync: workbook='{self.filepath}'>"

    # MANDATORY PROTOCOL MEMBERS

    @property
    def name(self) -> str:
        return "excel"

    def load(self, tab_name: str) -> list[dict[str, Any]]:
        t = self._get_or_create_tab(tab_name)

        if t.cell(1, 1).value is None:
            log.warning(f"no data found in tab '{tab_name}'!")
            return []

        head = [cell.value for cell in t[1]]
        data = [{h: c.value for h, c in zip(head, row)} for row in t[1:]]

        if not data:
            log.warning(f"no data found in tab '{tab_name}'!")
            return []

        return data

    def dump(self, tab_name: str, *, data: list[dict[str, Any]]) -> None:
        t = self._get_or_create_tab(tab_name)

        if not data:
            log.warning(f"no data to write to syncer {self}")
            return

        if self.mode == InsertMode.overwrite:
            t.delete_rows(0, t.max_row + 1)

        # write the header if it does not exist
        if t.cell(1, 1).value is None:
            for idx, name in enumerate(data[0].keys(), start=1):
                t.cell(1, idx, name)

        d = sanitize.clean_for_excel(data)
        [t.append(_) for _ in d]
        self.wb.save(self.filepath)
