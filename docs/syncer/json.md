---
icon: material/file
hide:
  - toc
---

 A JSON file is a way of storing and sharing data in a structured format that's easy for computers to read and understand. It's kind of like a digital version of a spreadsheet or a database, but it's designed to be more lightweight and flexible.

!!! note "JSON parameters"

    ### __Required__ parameters are in __red__{ .fc-red } and __Optional__ parameters are in __blue__{ .fc-blue }.
    
    ---

    - [x] __directory__{ .fc-red }, _the folder location to write JSON files to_

    ---

    - [ ] __encoding__{ .fc-blue }, _whether or not to accept double-byte characters, like japanese or cryillic_
    <br />__default__{ .fc-gray }: `None` ( __allowed__{ .fc-green }: `UTF-8` )


??? question "How do I use the JSON syncer in commands?"

    `cs_tools tools searchable bi-server --syncer json://directory=.`

    __- or -__{ .fc-blue }

    `cs_tools tools searchable bi-server --syncer json://definition.toml`


## Definition TOML Example

`definition.toml`
```toml
[configuration]
directory = '...'
```