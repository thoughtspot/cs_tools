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


SQLite is a C-language library that implements a small, fast, self-contained, high-reliability, full-featured, SQL database engine. SQLite is the most used database engine in the world. The SQLite file format is stable, cross-platform, and backwards compatible and the developers pledge to keep it that way through the year 2050.

??? info "Want to see the source code?"
    
    *If you're writing a Custom Syncer, you can check our project code for an example.*

    [cs_tools/sync/__SQLite__/syncer.py][syncer.py]

## SQLite `DEFINITION.toml` spec

> __database_path__{ .fc-blue }: name of the database to store data within
<br/>*`database` will be created if it does not exist*

> __truncate_on_load__{ .fc-blue }: <span class=fc-coral>optional</span>, either `true` or `false`
<br/>*<span class=fc-mint>default</span>:* `true`
<br/>*a* `TRUNCATE` *statement will be issued prior to loading any data loads if* `true` *is used*


??? question "How do I use the SQLite syncer in commands?"

    === ":fontawesome-brands-apple: Mac, :fontawesome-brands-linux: Linux"

        `cs_tools tools searchable bi-server sqlite:///home/user/syncers/sqlite-definition.toml --compact`

        `cs_tools tools searchable bi-server sqlite://default --compact`

    === ":fontawesome-brands-windows: Windows"

        `cs_tools tools searchable bi-server sqlite://C:\Users\%USERNAME%\Downloads\sqlite-definition.toml --compact`

        `cs_tools tools searchable bi-server sqlite://default --compact`

    *Learn how to register a default for syncers in [How-to: Setup a Configuration File][how-to-config].*


## Full Definition Example

`definition.toml`
```toml
[configuration]
database_path = '/home/user/ts-data/production.db'
```

[gh-issue25]: https://github.com/thoughtspot/cs_tools/issues/25
[syncer.py]: https://github.com/thoughtspot/cs_tools/blob/master/cs_tools/sync/sqlite/syncer.py
[how-to-config]: ../how-to/configuration-file.md
