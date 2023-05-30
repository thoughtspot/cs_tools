"""
This file contains code for the TML file system.  The TML file system is a structured file system for storing TML and
related files.
"""
import datetime
import logging
import pathlib
from abc import ABC
from typing import List

from thoughtspot_tml._tml import TML
from thoughtspot_tml.utils import determine_tml_type

from cs_tools._compat import StrEnum
from cs_tools.api import _utils
from cs_tools.cli.tools.scriptability.util import GUIDMapping, EnvName
from cs_tools.cli.ux import rich_console
from cs_tools.errors import CSToolsError
from cs_tools.types import GUID


class TMLType(StrEnum):
    """TML types.  These must map to what thoughtspot_tml.util.determine_tml_type returns."""
    connection = "connection"
    table = "table"
    view = "view"
    sql_view = "sql_view"
    sqlview = "sqlview"
    worksheet = "worksheet"
    answer = "answer"
    liveboard = "liveboard"
    pinboard = "pinboard"


class BaseTMLFileSystem(ABC):

    def __init__(self, path: pathlib.Path, log_for: str, logger: logging.Logger):
        """
        Creates a new TML File System object.  If the path does not exist, it will be created.
        :param path: The root path for the file system.
        :param log_for: The type of log file to create.  Must be "export" or "import".
        """
        if log_for not in ["export", "import"]:
            raise CSToolsError(error=f"Invalid log_for value: {log_for}.  Must be 'export' or 'import'.",
                               mitigation="Specify a valid log_for value.")

        self.path = path
        self.start_time = datetime.datetime.now()

        self._log_path = self._create_log_path(log_for=log_for)
        if logger:  # Add a file handler for logging.

            log_file = self._log_path / f"{log_for}-{self.start_time.strftime('%Y.%m.%d-%H.%M.%S')}.log"

            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))

            logger.addHandler(file_handler)

    def _create_log_path(self, log_for: str) -> pathlib.Path:
        """
        Creates a new log folder and sets the name for the log file.
        Note that this can create the path if it does not exist.
        """

        # make sure the path already exists.
        if not self.path.exists():
            raise CSToolsError(error=f"Path {self.path} does not exist.", mitigation="Specify a valid path to the FS.")

        # create the log folder and file.
        log_name = f"{log_for}-{self.start_time.strftime('%Y.%m.%d-%H.%M.%S')}"
        log_path = self.path / "logs" / log_name
        log_path.mkdir(parents=True, exist_ok=True)  # need full path in case the path doesn't yet exist.

        return log_path

    def log_tml(self, tml: TML, old_guid: GUID = None) -> None:
        """
        Logs a message to the import logs.   Note that this is determined by log time.   TODO - figure out
        :param tml: The message to log.
        """
        # A guid is being used for the file name.  Ideally use the old one if provided.  If not, use the new one.
        # If that doesn't exist, use the current time.
        guid = old_guid if old_guid else tml.guid if tml.guid else str(datetime.datetime.now())
        fn = guid + "." + tml.tml_type_name + ".tml"
        tml_file = self._log_path / fn
        tml.dump(tml_file)

    def get_mapping_file(self, source: str, dest: str) -> GUIDMapping:
        """
        Returns a mapping file based on the source and destination. If one doesn't exist, it will be created.
        :param source: The source of the TML, e.g. Dev.
        :param dest: The destination of the TML, e.g. Prod.
        :return: A mapping file.
        """

        # get the path to the file.  This assumes the folder structure has been set (e.g. via export).
        mapping_file_path = self.path / "guid-mappings" / f"{source}-{dest}.json"
        return GUIDMapping(source=EnvName(source), dest=EnvName(dest), path=mapping_file_path)

    @staticmethod
    def write_mapping_file(mapping_file: GUIDMapping) -> None:
        """
        Writes a mapping file to the file system.
        :param mapping_file: The mapping file to write.
        """
        mapping_file.save()


class ExportTMLFS(BaseTMLFileSystem):

    def __init__(self, path: pathlib.Path, logger: logging.Logger):
        super().__init__(path=path, log_for="export", logger=logger)
        self._create_tml_file_system(self.path)

    @classmethod
    def _create_tml_file_system(cls, path: pathlib.Path) -> None:
        """
        Create a new file system object.  If the path does not exist, it will be created.  The structure of the file
        system is:
        root
        - .tmlfs - hidden file with info about the file system.
        - guid-mappings - guid mapping files with names of the form <source>-<dest>.json
        - logs - log and import files
          - export-yyyy.mm.dd-hh.mm.ss.log - log file for export
          - import-yyyy.mm.dd-hh.mm.ss.log - log file for import
          - imported - imported files
            - yyyy.mm.dd-hh.mm.ss - folder for import
        - connections - connection files
        - tables - table files
        - views - view files
        - sql-views - SQL view files
        - worksheets - worksheet files
        - answers - answer files
        - liveboards - liveboard files
        :param path: The root path for the file system.  The FS will be created if it doesn't exist.  sub-folders will
                     be created as needed to make sure they stay consistent with the structure.
        """
        if path.exists():
            if not path.is_dir():
                raise CSToolsError(f"TML Path {path} exists but is not a directory.")
            else:
                fsfile = path / ".tmlfs"
                if not fsfile.exists():
                    rich_console.log(f"Creating TML File System at {path}")

        # now create the sub-folders.  If they already exist, then the creation will be ignored.
        (path / "logs").mkdir(exist_ok=True)
        (path / "guid-mappings").mkdir(exist_ok=True)

        for tml_type in TMLType:
            (path / tml_type).mkdir(exist_ok=True)

    def write_tml(self, tml: TML) -> None:
        """
        Writes the TML to the file system.
        :param tml: A TML object to write.  The name will be of the format <guid>.<type>.tml
        """
        try:
            tml_type = tml.tml_type_name
            directory = self.path / tml_type
            tml.dump(directory / f"{tml.guid}.{tml_type}.tml")
        except Exception as e:
            raise CSToolsError(error=f"Error writing TML {tml.name} to {directory}: {e}",
                               mitigation="Check write permissions in the file system..")


class ImportTMLFS(BaseTMLFileSystem):

    def __init__(self, path: pathlib.Path, logger: logging.Logger):
        super().__init__(path=path, log_for="import", logger=logger)

    def load_tml(self, types: [TMLType] = None) -> List[TML]:
        """
        Returns TML that matches the types requested.  If no types are specified, then all TML will be returned.
        :return: A list of TML.
        """

        types_to_load = [_ for _ in types] if types else [_ for _ in TMLType]
        tml_list: List[TML] = []

        for t in types_to_load:
            directory = self.path / t
            for f in directory.glob("*.tml"):
                tml_cls = determine_tml_type(path=f)
                tml = tml_cls.load(f)
                name, dot, extra = f.name.split(".")  # assumes that the file name is <guid>.<type>.tml

                if tml.guid is None and _utils.is_valid_guid(name):
                    tml.guid = name

                tml_list.append(tml)

        return tml_list

    def load_tml_for_guid(self, guid: GUID) -> TML:
        """
        Loads an individual TML by GUID.  This assumes that there is only one file with the given GUID and the file
        names are of the format <guid>.<type>.tml
        :param guid: The GUID to load.
        :return: The TML for the given GUID.
        """

        for t in [_ for _ in TMLType]:
            directory = self.path / t
            for f in directory.glob("*.tml"):
                name, dot, extra = f.name.split(".")
                if name == guid:
                    tml_cls = determine_tml_type(path=f)
                    return tml_cls.load(f)

        raise CSToolsError(error=f"Could not find TML with GUID {guid}.", mitigation="Check the GUID and try again.")
