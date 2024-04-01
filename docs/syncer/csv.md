---
hide:
  - toc
---

A CSV file, or __Comma-Separated Values__ file, is a simple type of spreadsheet or database file. It's a way to store and share data in a structured format that's easy for computers to read and understand. Each line of the file is a data record. Each record consists of one or more fields, separated by commas.

A CSV file typically stores tabular data in plain text, in which case each line will have the same number of fields. Alternative delimiter-separated files are often given a ".csv" extension despite the use of a non-comma field separator.

!!! note "CSV parameters"

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


??? question "How do I use the CSV syncer in commands?"

    `cs_tools tools searchable bi-server --syncer csv://directory=.&header=false&save_strategy=APPEND`

    __- or -__{ .fc-blue }

    `cs_tools tools searchable bi-server --syncer csv://definition.toml`


## Definition TOML Example

`definition.toml`
```toml
[configuration]
directory = '...'
delimiter = '|'
escape_character = '\'
save_strategy = APPEND
```