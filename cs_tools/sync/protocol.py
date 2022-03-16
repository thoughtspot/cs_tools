from dataclasses import dataclass
from typing import Protocol, Any, Dict, List

# also available
from pydantic.dataclasses import dataclass


RECORDS_FORMAT = List[Dict[str, Any]]


@dataclass
class SyncerProtocol(Protocol):
    """
    Implements a way to load and dump data to a data source.

    Defining a syncer allows CS Tools to interact with a data storage layer
    in an abstract way. You do not need to import SyncerProtocol in order to
    implement a custom one!

    To follow the Syncer protocol, you must..

        - define a class in syncer.py with 3 members   .name, .load(), .dump()
        - not override cls.__init__()

    Users will provide a DEFINITION.toml file to configure the behavior of a
    syncer. The details of each definition are relevant to which syncer is to
    be used. For example if you are to use the Excel syncer, you might specify
    a filepath to the target workbook, while if you use the Database syncer,
    the target database connection details might be required.

    If you are defining a custom syncer, there are 2-3 additional requirements:

        - a MANIFEST.json in the same path as syncer.py, with top-level keys..
          - `name`, the protocol name, e.g. "gsheets" for google sheets
          - `syncer_class`, the class name of your syncer protocol in syncer.py
          - optional `requirements`, an array in pip-friendly requirements spec

        - the DEFINITION.toml must have a top-level reference for
          `manifest` which is the absolute filepath to your MANIFEST.json

        - if you are implementing a database-specific syncer, you must also
          define a truthy attribute `__is_database__`, which triggers creation
          tables of tables in the database. (Pro tip: register a sqlalchemy
          listener for after_create to capture .metadata!)

    Data is expressed to and from the syncer in standardized json format. The
    data should behave like a list of flat dictionaries. This format is most
    similar to how you would conceptualize an ANSI SQL table in-memory.

        data = [
            {'guid': '308da7a3-cac0-42c8-bb74-3b05ba9281a3', 'username': 'tsadmin', ...},
            {'guid': 'c0fcfcdd-e7a9-404b-9aab-f541a8d7fed3', 'username': 'cs_tools', ...},
            ...,
            {'guid': '1b3c6f8d-9dc5-4515-a4fc-c47bfbad4bce', 'username': 'namey.namerson', ...}
        ]

    ** It is recommended to use either standard library or pydantic's
    `dataclasses.dataclass` for your Syncer. This is primarily so you can
    augment instance creation and setup through the use of the __post_init__ or
    __post_init__post_parse__ methods. Only a single Syncer will be created per
    run.

        See below references for more information.
          https://docs.python.org/3/library/dataclasses.html
          https://pydantic-docs.helpmanual.io/usage/dataclasses
    """
    name: str

    def load(self, identifier: str) -> RECORDS_FORMAT:
        """
        Extract data from the data storage layer.

        Parameters
        ----------
        identifier: str
          resource name within the storage layer to extract data from
          
          examples
          --------
            - database identifier could be a fully qualified tablename
            - excel identifier could be the name of a tab
            - csv identifier could be the name of a file

        Returns
        -------
        records: list-like of dictionaries
          data to return to cs_tools

          format should behave like a list of dictionaries..
            [{column: value}, ..., {column: value}]
        """

    def dump(self, identifier: str, *, data: RECORDS_FORMAT) -> None:
        """
        Persist data to the data storage layer.

        Parameters
        ----------
        identifier: str
          resource name within the storage layer to extract data from
          
          examples
          --------
            - database identifier could be a fully qualified tablename
            - excel identifier could be the name of a tab
            - csv identifier could be the name of a file

        data: list-like of dictionaries
          data to persist

        Returns
        -------
        records: list-like of dictionaries

          format should behave like a list of dictionaries..
            [{column: value}, ..., {column: value}]
        """
