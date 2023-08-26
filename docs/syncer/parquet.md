---
hide:
  - toc
---

??? example "In Beta"

    The Syncer protocol is in beta, it has been added to __CS Tools__ in v1.3 on a
    __provisional basis__. It may change significantly in future releases and its
    interface will not be concrete until v2.

    Feedback from the community while it's still provisional would be extremely useful;
    either comment on [#25][gh-issue25] or create a new issue.

Apache Parquet is an open source, column-oriented data file format designed for efficient data storage and retrieval. It provides efficient data compression and encoding schemes with enhanced performance to handle complex data in bulk.

??? info "Want to see the source code?"
    
    *If you're writing a Custom Syncer, you can check our project code for an example.*

    [cs_tools/sync/__parquet__/syncer.py][syncer.py]


## Parquet `DEFINITION.toml` spec

> __directory__{ .fc-blue }: file location to write parquet data to

> __compression__{ .fc-blue }: <span class=fc-coral>optional</span>, one of: __gzip__ or __snappy__
<br/>*<span class=fc-mint>default</span>:* `gzip`


??? question "How do I use the Parquet syncer in commands?"

    === ":fontawesome-brands-apple: Mac, :fontawesome-brands-linux: Linux"

        `cs_tools tools searchable bi-server parquet:///home/user/syncers/parquet-definition.toml --compact`

        `cs_tools tools searchable bi-server parquet://default --compact`

    === ":fontawesome-brands-windows: Windows"

        `cs_tools tools searchable bi-server parquet://C:\Users\%USERNAME%\Downloads\parquet-definition.toml --compact`

        `cs_tools tools searchable bi-server parquet://default --compact`

    *Learn how to register a default for syncers in [How-to: Setup a Configuration File][how-to-config].*


## Full Definition Example

`definition.toml`
```toml
[configuration]
directory = 'C:\Users\NameyNamerson\Downloads\thoughtspot'
compression = 'gzip'
```

[gh-issue25]: https://github.com/thoughtspot/cs_tools/issues/25
[syncer.py]: https://github.com/thoughtspot/cs_tools/blob/master/cs_tools/sync/parquet/syncer.py
[how-to-config]: ../tutorial/config.md
