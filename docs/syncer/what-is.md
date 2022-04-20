---
hide:
  - toc
---

Syncers allow __CS Tools__ to interact with a data storage layer without having to know
the explicit details of how to do so. We've implemented syncers to many popular data
storage formats.

!!! attention "In Beta"

    The Syncer protocol is in beta, it has been added to __CS Tools__ in v1.3 on a
    __provisional basis__. It may change significantly in future releases and its
    interface will not be concrete until v2.

    Feedback from the community while it's still provisional would be extremely useful;
    either comment on [#25][gh-issue25] or create a new issue.

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

In order to configure connection to your external data storage format, users will be
required to supply a `definition.toml` file. The details of each definition are relevant
to which syncer is used.

For example if you are to use the Excel syncer, you might specify a filepath to the
target workbook, while if you use the Database syncer, database connection details might
be required.

??? info "some examples of `DEFINITION.toml`"

    Definition files are your Users' way of configuring the Syncer's behavior. They do
    not need to be complex to enable versatile behavior.

    === ":material-code-json: JSON"
        ```toml
        [configuration]
        path = '/home/user/ts-data/production.json'
        ```

    === ":material-database: SQLite"
        ```toml
        [configuration]
        database_path = '/home/user/ts-data/production.db'
        truncate_on_load = True
        ```

    === ":material-google-spreadsheet: Google Sheets"
        ```toml
        [configuration]
        spreadsheet = 'ThoughtSpot Data Sink'
        mode = 'overwrite'
        credentials_file = '/home/user/ts-data/<project-name>-<uuid>.json'
        ```

    === ":material-new-box: Custom Syncer"
        ```toml
        manifest = '/home/user/syncers/foo-syncer/MANIFEST.json'

        [configuration]
        ...
        ```
        \* *custom syncers must supply the path to the MANIFEST.json file*

If your data format is not yet implemented, read on to the next page to learn about the
syncer protocol and be able to write your own custom syncer.


[gh-issue25]: https://github.com/thoughtspot/cs_tools/issues/25
