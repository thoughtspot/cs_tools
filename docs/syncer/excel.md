---
icon: material/file
hide:
  - toc
---

!!! note "Parameters"

    ### __Required__ parameters are in __red__{ .fc-red } and __Optional__ parameters are in __blue__{ .fc-blue }.
    
    ---

    - [x] __filepath__{ .fc-red }, *the file location to write the Excel file to*

    ---

    - [ ] __filepath_suffix__{ .fc-blue }, *an optional suffix to add to the Excel file, based on CURRENT DATETIME.*
    <br />__default__{ .fc-gray }: `None` ( use the [strftime.org](https://strftime.org) cheatsheet as a guide )

    ---

    - [ ] __date_time_format__{ .fc-blue }, *the string representation of date times*
    <br />__default__{ .fc-gray }: `%Y-%m-%dT%H:%M:%S.%f` ( use the [strftime.org](https://strftime.org) cheatsheet as a guide )

    ---

    - [ ] __save_strategy__{ .fc-blue }, *how to save new data into an existing directory*
    <br />__default__{ .fc-gray }: `OVERWRITE` ( __allowed__{ .fc-green }: `APPEND`, `OVERWRITE` )

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
        cs_tools tools searchable metadata --syncer "excel://filepath=searchable.xlsx" --config dogfood
        ```

        <sup class=fc-gray><i>* when declaring multiple parameters inline, you should <b class=fc-purple>wrap the enter value</b> in quotes.</i></sup>

    === ":recycle: &nbsp; Configuration File"

        1. Create a file with `.toml` extension.

            ??? abstract "syncer-overwrite.toml"
                ```toml
                [configuration]
                filepath = "searchable.xlsx"
                filepath_suffix = "--generated-on-%Y-%m-%d"
                date_time_format = "%Y-%m-%dT%H:%M:%S%z"
                save_strategy = "OVERWRITE"
                ```
                <sup class=fc-gray><i>* this is a complete example, not all parameters are <b class=fc-red>required</b>.</i></sup>

        2. Reference the filename in your command in place of the parameters.

            ```bash
            cs_tools tools searchable metadata --syncer excel://syncer-overwrite.toml --config dogfood
            ```

[cs-tools-serverless]: ../../getting-started/#__tabbed_1_4
[syncer-manifest]: https://github.com/thoughtspot/cs_tools/blob/master/cs_tools/sync/excel/MANIFEST.json
