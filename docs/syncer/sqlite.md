---
icon: material/database
hide:
  - toc
---

!!! note "Parameters"

    ### __Required__ parameters are in __red__{ .fc-red } and __Optional__ parameters are in __blue__{ .fc-blue }.
    
    ---

    - [X] __database_path__{ .fc-red }, *the full path to a sqlite database*
    <br />*this filepath may not yet exist, but it __must__{ .fc-red } end in `.db`*

    ---

    - [ ] __pragma_speedy_inserts__{ .fc-blue }, *whether or not to set* [`PRAGMAs`][sqlite-pragmas] *to improve* `INSERT` *performance*
    <br />__default__{ .fc-gray }: `False` ( __allowed__{ .fc-green }: `True`, `False` )

    ---

    - [ ] __load_strategy__{ .fc-blue}, *how to write new data into existing tables*
    <br />__default__{ .fc-gray }: `APPEND` ( __allowed__{ .fc-green }: `APPEND`, `TRUNCATE`, `UPSERT` )


??? question "How do I use the Syncer in commands?"

    __CS Tools__ accepts syncer definitions in either declarative or configuration file form.

    <sub class=fc-blue>Find the copy button :material-content-copy: to the right of the code block.</sub>

    === ":mega: &nbsp; Declarative"

        Simply write the parameters out alongside the command.

        ```bash
        cs_tools tools searchable metadata --syncer "sqlite://database_path=thoughtspot.db" --config dogfood
        ```

        <sup class=fc-gray><i>* when declaring multiple parameters inline, you should <b class=fc-purple>wrap the enter value</b> in quotes.</i></sup>

    === ":recycle: &nbsp; Configuration File"

        1. Create a file with `.toml` extension.

            ??? abstract "syncer-overwrite.toml"
                ```toml
                [configuration]
                database_path = "thoughtspot.db"
                pragma_speedy_inserts = true
                load_strategy = "TRUNCATE"
                ```
                <sup class=fc-gray><i>* this is a complete example, not all parameters are <b class=fc-red>required</b>.</i></sup>

        2. Reference the filename in your command in place of the parameters.

            ```bash
            cs_tools tools searchable metadata --syncer sqlite://syncer-overwrite.toml --config dogfood
            ```

[cs-tools-serverless]: ../../getting-started/#serverless
[syncer-manifest]: https://github.com/thoughtspot/cs_tools/blob/master/cs_tools/sync/sqlite/MANIFEST.json
[sqlite-pragmas]: https://www.sqlite.org/pragma.html