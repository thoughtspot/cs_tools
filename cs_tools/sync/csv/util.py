from __future__ import annotations

from operator import attrgetter
from typing import TYPE_CHECKING, Any
import datetime as dt
import zipfile

if TYPE_CHECKING:
    import io


def clean_datetime(row: dict[str, Any], *, date_time_format: str) -> dict[str, Any]:
    """
    Enforce a specific format for datetime values.
    """
    out = {}

    for key, value in row.items():
        if isinstance(value, (dt.datetime, dt.date)):
            value = value.strftime(date_time_format)

        out[key] = value

    return out


class StringToBytesAdapter:
    """
    Convert input data from string to bytes.

    zipfile.ZipFile.open() will return a member of the archive as a binary
    file-like object, however csv.writer dialects accept string data only. So
    we can write an adapter that automatically encodes the data.
    """

    def __init__(self, csv_in_zipfile: io.BytesIO):
        self.csv_in_zipfile = csv_in_zipfile
        self.close = self.csv_in_zipfile.close

    def write(self, data: str) -> None:
        self.csv_in_zipfile.write(data.encode())


class ZipFile(zipfile.ZipFile):
    """
    Open a ZIP file.

    Extends the builtin zipfile implementation to allow removal of files.

    DEV NOTE:

        We can probably clean this implementation up a little bit more, but it
        works now and cleanliness is a problem for bored future-me.
    """

    def open(self, member: str, *, mode: str = "r", remove: bool = True) -> StringToBytesAdapter:
        """
        Access a member of the archive as a binary file-like object.

        This file-like object will be passed to csv.reader and csv.writer,
        which prefer their data in str format. We are however a zipfile, which
        enforces writes to disk in bytes. We're gonna need to adapt that.

        Parameters
        ----------
        member: str
          name of a file within the archive

        mode: str, default 'r'
          either 'r' for read, or 'w' for write

        remove: bool, default True
          if the file already exists and we plan to append, delete it.

        Returns
        -------
        string-like file: StringToBytesAdapter
        """
        if remove and mode == "a" and member in self.namelist():
            self.remove(member)

        f: io.IOBase = super().open(member, mode=mode)
        return StringToBytesAdapter(f)

    def remove(self, member: str) -> None:
        """
        Remove a file from the archive.

        The archive must be open with mode 'a'.

        Parameters
        ----------
        member: str
          filename of the member to remove from the archive

        Returns
        -------
        None
        """
        if self.mode != "a":
            raise RuntimeError("remove() requires mode 'a'")
        if not self.fp:
            raise ValueError("Attempt to write to ZIP archive that was already closed")
        if self._writing:
            raise ValueError("Can't write to ZIP archive while an open writing handle exists.")

        if not isinstance(member, zipfile.ZipInfo):
            member = self.getinfo(member)

        self._remove_member(member)

    def _remove_member(self, member: zipfile.ZipInfo) -> None:
        # NOTE: cpython: 659eb048cc9cac73c46349eb29845bc5cd630f09/Lib/zipfile.py#L1717

        # get a sorted filelist by header offset, in case the dir order
        # doesn't match the actual entry order
        entry_offset = 0
        filelist = sorted(self.filelist, key=attrgetter("header_offset"))

        for i, info in enumerate(filelist):
            # find the target member
            if info.header_offset < member.header_offset:
                continue

            # get the total size of the entry
            entry_size = None
            if i == len(filelist) - 1:
                entry_size = self.start_dir - info.header_offset
            else:
                entry_size = filelist[i + 1].header_offset - info.header_offset

            # found the member, set the entry offset
            if member == info:
                entry_offset = entry_size
                continue

            # Move entry
            # read the actual entry data
            self.fp.seek(info.header_offset)
            entry_data = self.fp.read(entry_size)

            # update the header
            info.header_offset -= entry_offset

            # write the entry to the new position
            self.fp.seek(info.header_offset)
            self.fp.write(entry_data)
            self.fp.flush()

        # update state
        self.start_dir -= entry_offset
        self.filelist.remove(member)
        del self.NameToInfo[member.filename]
        self._didModify = True

        # seek to the start of the central dir
        self.fp.seek(self.start_dir)
