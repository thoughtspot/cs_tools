---
icon: material/database
hide:
  - toc
---

SQLite is a powerful, lightweight, and embedded database management system that has been around for over 20 years. It's a great choice for a wide range of applications, from mobile apps and embedded systems to desktop software and web applications. 

Unlike traditional database management systems that require a separate server process, SQLite is self-contained and serverless. This means that the entire database is stored in a single file on the local file system, making it incredibly easy to set up and use.

!!! note "SQLite parameters"

    ### __Required__ parameters are in __red__{ .fc-red } and __Optional__ parameters are in __blue__{ .fc-blue }.
    
    ---

    - [X] __database_path__{ .fc-red }, _the full path to a sqlite database_
    <br />_this filepath may not yet exist, but it __must__{ .fc-red } end in `.db`_

    ---

    - [ ] __load_strategy__{ .fc-blue}, _how to write new data into existing tables_
    <br />__default__{ .fc-gray }: `APPEND` ( __allowed__{ .fc-green }: `APPEND`, `TRUNCATE`, `UPSERT` )


??? question "How do I use the SQLite syncer in commands?"

    `cs_tools tools searchable bi-server --syncer sqlite://database_path=data.db`

    __- or -__{ .fc-blue }

    `cs_tools tools searchable bi-server --syncer sqlite://definition.toml`


## Definition TOML Example

`definition.toml`
```toml
[configuration]
database_path = '...'
load_strategy = 'truncate'
```
