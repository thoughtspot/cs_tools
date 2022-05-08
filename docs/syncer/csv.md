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

A __comma-separated values__ (CSV) file is a delimited text file that uses a comma to separate values. Each line of the file is a data record. Each record consists of one or more fields, separated by commas.

A CSV file typically stores tabular data in plain text, in which case each line will have the same number of fields. Alternative delimiter-separated files are often given a ".csv" extension despite the use of a non-comma field separator.

??? info "Want to see the source code?"
    
    *If you're writing a Custom Syncer, you can check our project code for an example.*

    [cs_tools/sync/__csv__/syncer.py][syncer.py]


## CSV `DEFINITION.toml` spec

> __directory__{ .fc-blue }: file location to write CSV data to

> __delimiter__{ .fc-blue }: <span class=fc-coral>optional</span>, one-character string used to separate fields
<br/>*<span class=fc-mint>default</span>:* `|` *the pipe character will be used*

> __escape_character__{ .fc-blue }: <span class=fc-coral>optional</span>, one-character string used to escape the delimiter
<br/>*<span class=fc-mint>default</span>: no escaping happens*

> __zipped__{ .fc-blue }: <span class=fc-coral>optional</span>, whether or not to zip the directory after writing all files
<br/>*<span class=fc-mint>default</span>:* `false`


??? question "How do I use the CSV syncer in commands?"

    === ":fontawesome-brands-apple: Mac, :fontawesome-brands-linux: Linux"

        `cs_tools tools searchable bi-server csv:///home/user/syncers/csv-definition.toml --compact`

        `cs_tools tools searchable bi-server csv://default --compact`

    === ":fontawesome-brands-windows: Windows"

        `cs_tools tools searchable bi-server csv://C:\Users\%USERNAME%\Downloads\csv-definition.toml --compact`

        `cs_tools tools searchable bi-server csv://default --compact`

    *Learn how to register a default for syncers in [How-to: Setup a Configuration File][how-to-config].*


## Full Definition Example

`definition.toml`
```toml
[configuration]
directory = 'C:\Users\NameyNamerson\Downloads\thoughtspot'
delimiter = '|'
escape_character = '\'
zipped = true
```

[gh-issue25]: https://github.com/thoughtspot/cs_tools/issues/25
[syncer.py]: https://github.com/thoughtspot/cs_tools/blob/master/cs_tools/sync/csv/syncer.py
[how-to-config]: ../how-to/configuration-file.md
