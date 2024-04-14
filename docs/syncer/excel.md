---
icon: material/file
hide:
  - toc
---

An Excel file is a type of spreadsheet document that's created using Microsoft Excel, a popular computer program for working with data and numbers. It's kind of like a digital version of those old-school paper spreadsheets, but way more powerful and flexible.

!!! note "Excel parameters"

    ### __Required__ parameters are in __red__{ .fc-red } and __Optional__ parameters are in __blue__{ .fc-blue }.
    
    ---

    - [x] __filepath__{ .fc-red }, _the file location to write the Excel file to_

    ---

    - [ ] __date_time_format__{ .fc-blue }, _the string representation of date times_
    <br />__default__{ .fc-gray }: `%Y-%m-%dT%H:%M:%S.%f` ( use the [strftime.org](https://strftime.org) cheatsheet as a guide )
    
    ---

    - [ ] __save_strategy__{ .fc-blue }, _how to save new data into an existing directory_
    <br />__default__{ .fc-gray }: `OVERWRITE` ( __allowed__{ .fc-green }: `APPEND`, `OVERWRITE` )


??? question "How do I use the Excel syncer in commands?"

    `cs_tools tools searchable bi-server --syncer excel://filepath=data.xlsx&save_strategy=APPEND`

    __- or -__{ .fc-blue }

    `cs_tools tools searchable bi-server --syncer excel://definition.toml`


## Definition TOML Example

`definition.toml`
```toml
[configuration]
filepath = '...'
save_strategy = APPEND
```