---
hide:
  - toc
---

??? attention "In Beta"

    The Syncer protocol is in beta, it has been added to __CS Tools__ in v1.3 on a
    __provisional basis__. It may change significantly in future releases and its
    interface will not be concrete until v2.

    Feedback from the community while it's still provisional would be extremely useful;
    either comment on [#25][gh-issue25] or create a new issue.

If your use case for interacting with the ThoughtSpot API data isn't supported by the
built-in syncers in CS Tools, we've exposed an interface for defining a custom syncer so
that you can inject your own.

---

To follow the Syncer protocol, you must provide at least..

  - A `class` in `syncer.py` which has at least 3 members: `.name`, `.load()`, `.dump()`
  - `MANIFEST.json` which tells CS Tools how to register your custom syncer

..while a typical project directory follows the below format.

```
<custom-syncer>
├─ __init__.py
├─ ...
├─ syncer.py
└─ MANIFEST.json
```

Outside of these two file requirements, you are free to augment the interface in any way
you want! Custom Syncers are simply ad-hoc pure python packages, so you're able to
leverage the full python ecosystem.

!!! hint "Tip"

    You do not need to `import SyncerProtocol` in order to implement a custom one! Simply
    follow the 3 core requirements of defining a `.name` attribute, as well as `.load()`
    and `.dump()` members.

### `syncer.py`

```python
from dataclasses import dataclass
from typing import Any, Dict, List

# also available
from pydantic.dataclasses import dataclass


RECORDS_FORMAT = List[Dict[str, Any]]


@dataclass
class SyncerProtocol:
    """
    Implements a way to load and dump data to a data source.
    """
    name: str

    def load(self, identifier: str) -> RECORDS_FORMAT:
        """
        Extract data from the data storage layer.

        Parameters
        ----------
        identifier: str
          resource name within the storage layer to extract data from
        """

    def dump(self, identifier: str, *, data: RECORDS_FORMAT) -> None:
        """
        Persist data to the data storage layer.

        Parameters
        ----------
        identifier: str
          resource name within the storage layer to extract data from

        data: list-like of dictionaries
          data to persist
        """
```

??? info "Implementing a Database Syncer?"

    Database Syncers have special meaning in CS Tools. They interact with complex data
    stores, typically at a remote location.

    Set an attribute on your syncer class named `__is_database__` to any truthy value.
    This will tell CS Tools to run `metadata.create_all(syncer.cnxn)` prior to any
    calls to your syncer.

    Additonally, your syncer should expose an `cnxn` attribute, with a fully
    instantiated `sqlalchemy.engine.Engine` to interact with the database backend.

    🔥 __Pro tip__: during initialization, register a `sqlalchemy` event listener to
    capture the metadata during table creation.

    ```python
    import sqlalchemy as sa


    class FooSyncer:
        __is_database__ = True
        name = 'foo_syncer'

        def __post_init__(self):
            self.engine = sa.create_engine(...)
            self.cnxn = self.engine.connect()
            sa.event.listen(sa.schema.MetaData, 'after_create', self.capture_metadata)

        def capture_metadata(self, metadata, cnxn, **kw):
            self.metadata = metadata
    ```

Data is expressed to and from the syncer in standardized json format. The data should
behave like a list of flat dictionaries. This format is most similar to how you would
receive data back from many REST and DB-APIs.

```python
data = [
    {'guid': '308da7a3-cac0-42c8-bb74-3b05ba9281a3', 'username': 'tsadmin', ...},
    {'guid': 'c0fcfcdd-e7a9-404b-9aab-f541a8d7fed3', 'username': 'cs_tools', ...},
    ...,
    {'guid': '1b3c6f8d-9dc5-4515-a4fc-c47bfbad4bce', 'username': 'namey.namerson', ...}
]
```

!!! tip "Tip"

    It's highly recommended to either the standard library's or pydantic's `dataclass`
    paradigm for your Syncer. This will easily allow you to set up your syncer without
    overriding the `__init__` method.

    If you're using `dataclasses`, leverage the `__post_init__` method.

    If you're using `pydantic`, leverage the `__post_init__post_parse__` method.

    **See below references for more information.**
     
      - [`dataclasses.dataclass`](https://docs.python.org/3/library/dataclasses.html) 
      - [`pydantic.dataclasses.dataclass`](https://pydantic-docs.helpmanual.io/usage/dataclasses)

---

The other required file is a MANIFEST which tells CS Tools how to utilize your Syncer.
This JSON file should live in same directory as your `syncer.py`. It should contain 
top-level keys in order to inform CS Tools how to set it up.

> `name`: the name of your custom syncer protocol

> `syncer_class`: the python class which contains your syncer's code

> `requirements`: an array of pip-friendly requirements to have installed prior to code
execution

### `MANIFEST.json`

```json
{
    "name": "<custom-syncer>",
    "syncer_class": "CustomSyncer",
    "requirements": [
        "package>=X.Y.Z"
    ]
}
```

??? example "See it in action"

    Want to see example code of how to implement your own syncer? Check out the built-in
    ones!

    - [CSV](https://github.com/thoughtspot/cs_tools/tree/master/cs_tools/sync/csv){ .external-link }
    - [SQLite](https://github.com/thoughtspot/cs_tools/tree/master/cs_tools/sync/sqlite){ .external-link }
    - [Snowflake](https://github.com/thoughtspot/cs_tools/tree/master/cs_tools/sync/snowflake){ .external-link }


[gh-issue25]: https://github.com/thoughtspot/cs_tools/issues/25
