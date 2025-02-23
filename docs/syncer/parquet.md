---
icon: material/file
hide:
  - toc
---

!!! note "Parameters"

    ### __Required__ parameters are in __red__{ .fc-red } and __Optional__ parameters are in __blue__{ .fc-blue }.
    
    ---

    - [x] __directory__{ .fc-red }, *the folder location to write Parquet files to*

    ---

    - [ ] __compression__{ .fc-blue }, *the method used to compress data*
    <br />__default__{ .fc-gray }: `GZIP` ( __allowed__{ .fc-green }: `GZIP`, `SNAPPY` )

    ---

    ??? danger "Serverless Requirements"

        If you're running __CS Tools__ [&nbsp; :simple-serverless: &nbsp;__serverless__][cs-tools-serverless], you'll want to ensure you install these [&nbsp; :simple-python: &nbsp;__python requirements__][syncer-manifest].

        :cstools-mage: __Don't know what this means? It's probably safe to ignore it.__{ .fc-purple }


??? question "How do I use the Syncer in commands?"

    __CS Tools__ accepts syncer definitions in either declarative or configuration file form.

    <sub class=fc-blue>Find the copy button :material-content-copy: to the right of the code block.</sub>

    === ":mega: &nbsp; Declarative"

        Simply write the parameters out alongside the command.

        ```bash
        cs_tools tools searchable metadata --syncer "parquet://directory=." --config dogfood
        ```

        <sup class=fc-gray><i>* when declaring multiple parameters inline, you should <b class=fc-purple>wrap the enter value</b> in quotes.</i></sup>

    === ":recycle: &nbsp; Configuration File"

        1. Create a file with the `.toml` extension.

            ??? abstract "syncer-overwrite.toml"
                ```toml
                [configuration]
                directory = "."
                compression = "GZIP"
                ```
                <sup class=fc-gray><i>* this is a complete example, not all parameters are <b class=fc-red>required</b>.</i></sup>

        2. Write the filename in your command in place of the parameters.

            ```bash
            cs_tools tools searchable metadata --syncer parquet://syncer-overwrite.toml --config dogfood
            ```

[cs-tools-serverless]: ../../getting-started/#__tabbed_1_4
[syncer-manifest]: https://github.com/thoughtspot/cs_tools/blob/master/cs_tools/sync/parquet/MANIFEST.json