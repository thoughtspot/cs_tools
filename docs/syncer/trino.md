---
hide:
  - toc
---

 Trino is a powerful, open-source database tool that helps you analyze and explore large amounts of data really quickly. Imagine you have a bunch of data spread across different places - like files stored in the cloud, databases, and other data sources. Trino lets you access all of that data in one place, using standard SQL queries, without having to move or copy the data around.

!!! note "Trino parameters"

    ### __Required__ parameters are in __red__{ .fc-red } and __Optional__ parameters are in __blue__{ .fc-blue }.
    
    ---

    - [X] __host__{ .fc-red }, _the IP address or URL of your Trino catalog_

    ---

    - [ ] __port__{ .fc-blue }, _the port number where your Trino catalog is located_
    <br />__default__{ .fc-gray }: `8080`

    ---

    - [X] __catalog__{ .fc-red }, _the catalog to write new data to_
    <br />___if tables do not exist in the catalog.schema location already, we'll auto-create them___{ .fc-green }

    ---

    - [ ] __schema__{ .fc-blue }, _the schema to write new data to_
    <br />__default__{ .fc-gray }: `public`, ___if tables do not exist in the catalog.schema location already, we'll auto-create them___{ .fc-green }

    ---

    - [X] __authentication__{ .fc-red }, _the type of authentication mechanism to use to connect to Trino_
    <br />( __allowed__{ .fc-green }: `basic`, `jwt` )

    ---

    - [X] __username__{ .fc-red }, _your Trino username_

    ---

    - [ ] __secret__{ .fc-blue }, _the secret value to pass to the authentication mechanism_
    <br />_this will be either a __password__{ .fc-purple } or __json web token__{ .fc-purple }_

    ---

    - [ ] __load_strategy__{ .fc-blue}, _how to write new data into existing tables_
    <br />__default__{ .fc-gray }: `APPEND` ( __allowed__{ .fc-green }: `APPEND`, `TRUNCATE`, `UPSERT` )


??? question "How do I use the Trino syncer in commands?"

    `cs_tools tools searchable bi-server --syncer trino://host=0.0.0.0&catalog=...&schema=cs_tools&authentication=basic&username=admin&load_strategy=upsert`

    __- or -__{ .fc-blue }

    `cs_tools tools searchable bi-server --syncer trino://definition.toml`


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
