---
icon: material/file
hide:
  - toc
---

!!! note "Parameters"

    ### __Required__ parameters are in __red__{ .fc-red } and __Optional__ parameters are in __blue__{ .fc-blue }.
    
    ---

    - [x] __directory__{ .fc-red }, _the folder location to write CSV files to_

    ---

    - [ ] __delimiter__{ .fc-blue }, _a one-character string used to separate fields_
    <br />__default__{ .fc-gray }: `|`
 
    ---

    - [ ] __escape_character__{ .fc-blue }, _a one-character string used to escape the delimiter_
    <br />__default__{ .fc-gray }: `\\` ( if the escape character is itself, it must be escaped as well )

    ---

    - [ ] __empty_as_null__{ .fc-blue }, _whether or not to convert empty strings to the `None` sentinel_
    <br />__default__{ .fc-gray }: `false` ( __allowed__{ .fc-green }: `true`, `false` )
    
    ---

    - [ ] __quoting__{ .fc-blue }, _how to quote individual cell values_
    <br />__default__{ .fc-gray }: `MINIMAL` ( __allowed__{ .fc-green }: `ALL`, `MINIMAL` )
    
    ---

    - [ ] __date_time_format__{ .fc-blue }, _the string representation of date times_
    <br />__default__{ .fc-gray }: `%Y-%m-%d %H:%M:%S` ( use the [strftime.org](https://strftime.org) cheatsheet as a guide )
    
    ---

    - [ ] __header__{ .fc-blue }, _whether or not to write the column headers as the first row_
    <br />__default__{ .fc-gray }: `true` ( __allowed__{ .fc-green }: `true`, `false` )
    
    ---

    - [ ] __save_strategy__{ .fc-blue }, _how to save new data into an existing directory_
    <br />__default__{ .fc-gray }: `OVERWRITE` ( __allowed__{ .fc-green }: `APPEND`, `OVERWRITE` )


??? question "How do I use the Syncer in commands?"

    __CS Tools__ accepts syncer definitions in either declarative or configuration file form.

    <sub class=fc-blue>Find the copy button :material-content-copy: to the right of the code block.</sub>

    === ":mega: &nbsp; Declarative"

        Simply write the parameters out alongside the command.

        ```bash
        cs_tools tools searchable metadata --syncer "csv://directory=.&delimiter=|" --config dogfood
        ```

        <sup class=fc-gray><i>* when declaring multiple parameters inline, you should <b class=fc-purple>wrap the enter value</b> in quotes.</i></sup>

    === ":recycle: &nbsp; Configuration File"

        1. Create a file with the `.toml` extension.

            ??? abstract "syncer-overwrite.toml"
                ```toml
                [configuration]
                directory = "."
                delimiter = "|"
                escape_character = "\\"
                empty_as_null = true
                quoting = "ALL"
                date_time_format = "%Y-%m-%dT%H:%M:%S%z"
                header = false
                save_strategy = "APPEND"
                ```
                <sup class=fc-gray><i>* this is a complete example, not all parameters are <b class=fc-red>required</b>.</i></sup>

        2. Write the filename in your command in place of the parameters.

            ```bash
            cs_tools tools searchable metadata --syncer csv://syncer-overwrite.toml --config dogfood
            ```