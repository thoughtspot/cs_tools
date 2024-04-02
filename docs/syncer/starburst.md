---
hide:
  - toc
---

Starburst is a powerful, enterprise-grade data analytics platform that allows you to query and analyze data from a wide variety of sources, all in a single, unified environment. It's built on top of the open-source Trino (formerly Presto) query engine, which is known for its speed, scalability, and flexibility.

Unlike traditional database management systems that require you to move and transform your data into a centralized repository, Starburst lets you query data where it lives - whether that's in a data warehouse, a data lake, or even disparate databases and file systems across your organization. This "data mesh" approach helps you avoid the time and cost of complex ETL (extract, transform, load) processes, while still giving you the ability to access and analyze all your relevant data.

!!! note "Starburst parameters"

    ### __Required__ parameters are in __red__{ .fc-red } and __Optional__ parameters are in __blue__{ .fc-blue }.
    
    ---

    - [X] __host__{ .fc-red }, _the IP address or URL of your Starburst catalog_

    ---

    - [ ] __port__{ .fc-blue }, _the port number where your Starburst catalog is located_
    <br />__default__{ .fc-gray }: `8080`

    ---

    - [X] __catalog__{ .fc-red }, _the catalog to write new data to_
    <br />___if tables do not exist in the catalog.schema location already, we'll auto-create them___{ .fc-green }

    ---

    - [ ] __schema__{ .fc-blue }, _the schema to write new data to_
    <br />__default__{ .fc-gray }: `public`, ___if tables do not exist in the catalog.schema location already, we'll auto-create them___{ .fc-green }

    ---

    - [X] __authentication__{ .fc-red }, _the type of authentication mechanism to use to connect to Starburst_
    <br />( __allowed__{ .fc-green }: `basic`, `jwt` )

    ---

    - [X] __username__{ .fc-red }, _your Starburst username_

    ---

    - [ ] __secret__{ .fc-blue }, _the secret value to pass to the authentication mechanism_
    <br />_this will be either a __password__{ .fc-purple } or __jwt__{ .fc-purple }_

    ---

    - [ ] __load_strategy__{ .fc-blue}, _how to write new data into existing tables_
    <br />__default__{ .fc-gray }: `APPEND` ( __allowed__{ .fc-green }: `APPEND`, `TRUNCATE`, `UPSERT` )


??? question "How do I use the Starburst syncer in commands?"

    `cs_tools tools searchable bi-server --syncer starburst://host=0.0.0.0&catalog=...&schema=cs_tools&authentication=basic&username=admin&load_strategy=upsert`

    __- or -__{ .fc-blue }

    `cs_tools tools searchable bi-server --syncer starburst://definition.toml`


## Definition TOML Example

`definition.toml`
```toml
[configuration]
host = "0.0.0.0"
catalog = "..."
schema = "cs_tools"
authentication = "basic"
username = "admin"
load_strategy = "upsert"
```
