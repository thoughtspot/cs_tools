---
hide:
  - toc
---

Syncers allow CS Tools to interact with a data storage layer without having to know the
explicit details of how to do so.

---

<center>
``` mermaid
flowchart LR
  A[ThoughtSpot] --> | APIs | B{{searchable gather}};
  subgraph cs_tools
  B -.- | has a | C{Syncer};
  end
  C ---> | dump | D[Snowflake];
  D ---> | load | C;

  %% style A justify:contents,fill:#f9f,stroke:#333
```
*data flow diagram between ThoughtSpot and an external data source*
</center>

---

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
