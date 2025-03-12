---
icon: material/database
hide:
  - toc
---

??? tinm "There is No Magic!"

    __This Syncer uses [Databricks's SQLAlchemy driver][dbx-sqla] under the hood__.
    
    __Databricks__ states that it is intended to connect to [__Unity Catalog__][dbx-uc], and that usage with `hive_metastore` is untested.


!!! note "Parameters"

    ### __Required__ parameters are in __red__{ .fc-red } and __Optional__ parameters are in __blue__{ .fc-blue }.
    
    ---

    - [X] __server_hostname__{ .fc-red }, _your SQL Warehouse's host name_
    <br />*__this can be found on the Connection Details tab__*{ .fc-green }

    ---

    - [X] __http_path__{ .fc-red }, _your SQL Warehouse's path_
    <br />*__this can be found on the Connection Details tab__*{ .fc-green }
    
    ---

    - [X] __access_token__{ .fc-red }, _generate a personal access token from your SQL Warehouse_
    <br />*__this can be found on the Connection Details tab__*{ .fc-green }
    
    ---

    - [X] __catalog__{ .fc-red }, _the catalog to write new data to_
    <br />*__if tables do not exist in the__ `catalog.schema` __location already, we'll auto-create them__*{ .fc-green }

    ---

    - [ ] __schema__{ .fc-blue }, _the schema to write new data to_
    <br />*__if tables do not exist in the__ `database.schema` __location already, we'll auto-create them__*{ .fc-green }

    ---

    - [ ] __port__{ .fc-blue }, _the port number where your Databricks instance is exposed on_
    <br />__default__{ .fc-gray }: `443`
    
    ---

    - [ ] __use_legacy_dataload__{ .fc-blue }, _fall back to slower data loading with JDBC-style `INSERT`s_
    <br />__default__{ .fc-gray }: `false` ( __allowed__{ .fc-green }: `true`, `false` )

    ---

    - [ ] __load_strategy__{ .fc-blue}, _how to write new data into existing tables_
    <br />__default__{ .fc-gray }: `APPEND` ( __allowed__{ .fc-green }: `APPEND`, `TRUNCATE`, `UPSERT` )

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
        cs_tools tools searchable metadata --syncer "databricks://server_hostname=dbc-abc1234-efgh.cloud.databricks.com&http_path=/sql/protocolv1/o/1234567890123456/0123-456789-abcdef01&access_token=dapi0123456789abcdef0123456789abcdef&catalog=thoughtspot" --config dogfood
        ```

        <sup class=fc-gray><i>* when declaring multiple parameters inline, you should <b class=fc-purple>wrap the enter value</b> in quotes.</i></sup>

    === ":recycle: &nbsp; Configuration File"

        1. Create a file with the `.toml` extension.

            ??? abstract "syncer-overwrite.toml"
                ```toml
                [configuration]
                server_hostname = "dbc-abc1234-efgh.cloud.databricks.com"
                http_path = "/sql/protocolv1/o/1234567890123456/0123-456789-abcdef01"
                access_token = "dapi0123456789abcdef0123456789abcdef"
                catalog = "thoughtspot"
                schema = "cs_tools"
                port = 443
                load_strategy = "TRUNCATE"
                ```
                <sup class=fc-gray><i>* this is a complete example, not all parameters are <b class=fc-red>required</b>.</i></sup>

        2. Write the filename in your command in place of the parameters.

            ```bash
            cs_tools tools searchable metadata --syncer databricks://syncer-overwrite.toml --config dogfood
            ```

[cs-tools-serverless]: ../../getting-started/#serverless
[syncer-manifest]: https://github.com/thoughtspot/cs_tools/blob/master/cs_tools/sync/databricks/MANIFEST.json
[dbx-sqla]: https://docs.databricks.com/aws/en/dev-tools/sqlalchemy
[dbx-uc]: https://www.databricks.com/product/unity-catalog