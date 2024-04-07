---
hide:
  - toc
---

Databricks is a cloud-based data platform that helps companies manage and analyze large amounts of data from various sources. 

Databricks was originally created as a way to easily run Apache Spark, a powerful open-source data processing engine, without having to worry about the underlying infrastructure. It provided a user-friendly "notebook" interface where you could write code and run it on a scalable, distributed computing cluster in the cloud.

!!! note "Databricks parameters"

    ### __Required__ parameters are in __red__{ .fc-red } and __Optional__ parameters are in __blue__{ .fc-blue }.
    
    ---

    - [X] __server_hostname__{ .fc-red }, _your SQL Warehouse's host name_
    <br />_this can be found on the Connection Details tab_

    ---

    - [X] __http_path__{ .fc-red }, _your SQL Warehouse's path_
    <br />_this can be found on the Connection Details tab_
    
    ---

    - [X] __access_token__{ .fc-red }, _generate a personal access token from your SQL Warehouse_
    <br />_this can be generated on the Connection Details tab_
    
    ---

    - [X] __catalog__{ .fc-red }, _the catalog to write new data to_
    <br />___if tables do not exist in the catalog.schema location already, we'll auto-create them___{ .fc-green }

    ---

    - [ ] __schema__{ .fc-blue }, _the schema to write new data to_
    <br />___if tables do not exist in the database.schema location already, we'll auto-create them___{ .fc-green }

    ---

    - [ ] __port__{ .fc-blue }, _the port number where your Databricks instance is exposed on_
    <br />__default__{ .fc-gray }: `443`
    
    ---

    - [ ] __load_strategy__{ .fc-blue}, _how to write new data into existing tables_
    <br />__default__{ .fc-gray }: `APPEND` ( __allowed__{ .fc-green }: `APPEND`, `TRUNCATE`, `UPSERT` )


??? question "How do I use the Databricks syncer in commands?"

    `cs_tools tools searchable bi-server --syncer "databricks://server_hostname=...&http_path=...&access_token=...&catalog=..."`

    __- or -__{ .fc-blue }

    `cs_tools tools searchable bi-server --syncer databricks://definition.toml`


## Definition TOML Example

`definition.toml`
```toml
[configuration]
server_hostname = "..."
http_path = "..."
access_token = "..."
catalog = "..."
schema = 'CS_TOOLS'
load_strategy = 'truncate'
```

[snowflake-account-id]: https://docs.snowflake.com/en/user-guide/admin-account-identifier
[snowflake-auth]: https://docs.snowflake.com/en/developer-guide/node-js/nodejs-driver-authenticate