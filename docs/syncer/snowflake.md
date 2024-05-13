---
icon: material/database
hide:
  - toc
---

Snowflake is a powerful cloud-based data warehouse that makes it super easy to store, analyze, and share your company's data. It can handle massive amounts of information, from traditional spreadsheets to complex, unstructured data like web logs and sensor readings. The key thing that sets Snowflake apart is its unique architecture.

Instead of having a single, monolithic database, Snowflake separates the storage of your data from the computing power needed to analyze it. This means you can scale up or down the amount of processing power you use without having to worry about moving or reorganizing your data.

!!! note "Snowflake parameters"

    ### __Required__ parameters are in __red__{ .fc-red } and __Optional__ parameters are in __blue__{ .fc-blue }.
    
    ---

    - [X] __account_name__{ .fc-red }, _your Snowflake [account identifier][snowflake-account-id]_

    ---

    - [X] __username__{ .fc-red }, _your Snowflake username_
    
    ---

    - [X] __warehouse__{ .fc-red }, _the name of a Snowflake warehouse you have accces to_
    
    ---

    - [X] __role__{ .fc-red }, _the name of a Snowflake role you have access to_
    
    ---

    - [X] __authentication__{ .fc-red }, _the type of [authentication mechanism][snowflake-auth] to use to connect to Snowflake_
    <br />( __allowed__{ .fc-green }: `basic`, `key-pair`, `sso`, `oauth` )

    ---

    - [X] __database__{ .fc-red }, _the database to write new data to_
    <br />___if tables do not exist in the database.schema location already, we'll auto-create them___{ .fc-green }
    
    ---

    - [ ] __schema__{ .fc-blue }, _the schema to write new data to_
    <br />___if tables do not exist in the database.schema location already, we'll auto-create them___{ .fc-green }
    <br />__default__{ .fc-gray }: `PUBLIC`

    ---

    - [X] __secret__{ .fc-red }, _the secret value to pass to the authentication mechanism_
    <br />_this will be either a __password__{ .fc-purple } or __oauth token__{ .fc-purple }_
    
    ---

    - [ ] __private_key_path__{ .fc-blue }, _full path to an encrypted private key file_
    
    ---

    - [ ] __log_level__{ .fc-blue }, _the noisiness of the underlying Snowflake sql driver_
    <br />__default__{ .fc-gray }: `warning` ( __allowed__{ .fc-green }: `debug`, `info`, `warning` )
    
    ---

    - [ ] __temp_dir__{ .fc-blue }, _location to write temporary files prior to staging to Snowflake_
    <br />__default__{ .fc-gray }: `CS_TOOLS.TEMP_DIR` (your temporary directory in the CS Tools configuration)

    ---

    - [ ] __load_strategy__{ .fc-blue}, _how to write new data into existing tables_
    <br />__default__{ .fc-gray }: `APPEND` ( __allowed__{ .fc-green }: `APPEND`, `TRUNCATE`, `UPSERT` )


??? question "How do I use the Snowflake syncer in commands?"

    `cs_tools tools searchable bi-server --syncer snowflake://account_name=...&username=...&secret=...&warehouse=WH_DATA_LOADS_XS&role=DATA_OPERATIONS&database=GO_TO_MARKET&authentication=basic`

    __- or -__{ .fc-blue }

    `cs_tools tools searchable bi-server --syncer snowflake://definition.toml`


## Definition TOML Example

`definition.toml`
```toml
[configuration]
account_name = '...'
username = '...'
secret = '...'
warehouse = 'WH_DATA_LOADS_XS'
role = 'DATA_OPERATIONS'
database = 'GO_TO_MARKET'
schema = 'CS_TOOLS'
authentication = 'basic'
load_strategy = 'truncate'
```

[snowflake-account-id]: https://docs.snowflake.com/en/user-guide/admin-account-identifier
[snowflake-auth]: https://docs.snowflake.com/en/developer-guide/node-js/nodejs-driver-authenticate