---
icon: material/database
hide:
  - toc
---

!!! note "Parameters"

    ### __Required__ parameters are in __red__{ .fc-red } and __Optional__ parameters are in __blue__{ .fc-blue }.
    
    ---

    - [X] __account_name__{ .fc-red }, *your Snowflake [account identifier][snowflake-account-id]*
    <br />*__for most customers, this is your account name__*{ .fc-green }
    <br />*__if you are using Privatelink, use the format__ `<account>.<region>.privatelink`*{ .fc-green }

    ---

    - [X] __username__{ .fc-red }, *your Snowflake username*
    
    ---

    - [X] __warehouse__{ .fc-red }, *the name of a Snowflake warehouse you have accces to*
    
    ---

    - [X] __role__{ .fc-red }, *the name of a Snowflake role you have access to*
    
    ---

    - [X] __authentication__{ .fc-red }, *the type of [authentication mechanism][snowflake-auth] to use to connect to Snowflake*
    <br />( __allowed__{ .fc-green }: `basic`, `key-pair`, `sso`, `oauth` )

    ---

    - [X] __database__{ .fc-red }, *the database to write new data to*
    <br />*__if tables do not exist in the__ `database.schema` __location already, we'll auto-create them__*{ .fc-green }
    
    ---

    - [ ] __schema__{ .fc-blue }, _the schema to write new data to_
    <br />*__if tables do not exist in the__ `database.schema` __location already, we'll auto-create them__*{ .fc-green }
    <br />__default__{ .fc-gray }: `PUBLIC`

    ---

    - [X] __secret__{ .fc-red }, *the secret value to pass to the authentication mechanism*
    <br />*__this will be either a <span class=fc-purple>password</span> or <span class=fc-purple>oauth token</span>__*{ .fc-green }
    
    ---

    - [ ] __private_key_path__{ .fc-blue }, *full path to an encrypted private key file*
    
    ---

    - [ ] __log_level__{ .fc-blue }, *the noisiness of the underlying Snowflake sql driver*
    <br />__default__{ .fc-gray }: `warning` ( __allowed__{ .fc-green }: `debug`, `info`, `warning` )
    
    ---

    - [ ] __temp_dir__{ .fc-blue }, *location to write temporary files prior to staging to Snowflake*
    <br />__default__{ .fc-gray }: `CS_TOOLS.TEMP_DIR` (your temporary directory in the CS Tools configuration)

    ---

    - [ ] __load_strategy__{ .fc-blue}, *how to write new data into existing tables*
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
        cs_tools tools searchable metadata --syncer "snowflake://account_name=thoughtspot&username=tsadmin&warehouse=ETL_WH&role=ACCT_DATA_LOADER&authentication=basic&database=thoughtspot&schema=cs_tools&secret=[redacted]" --config dogfood
        ```

        <sup class=fc-gray><i>* when declaring multiple parameters inline, you should <b class=fc-purple>wrap the enter value</b> in quotes.</i></sup>

    === ":recycle: &nbsp; Configuration File"

        1. Create a file with the `.toml` extension.

            ??? abstract "syncer-overwrite.toml"
                ```toml
                [configuration]
                account_name = "thoughtspot"
                username = "tsadmin"
                warehouse = "ETL_WH"
                role = "ACCT_DATA_LOADER"
                authentication = "basic"
                database = "thoughtspot"
                schema = "cs_tools"
                secret = "[redacted]"
                # private_key_path = ...
                log_level = "info"
                temp_dir = "/tmp"
                load_strategy = "TRUNCATE"
                ```
                <sup class=fc-gray><i>* this is a complete example, not all parameters are <b class=fc-red>required</b>.</i></sup>

        2. Write the filename in your command in place of the parameters.

            ```bash
            cs_tools tools searchable metadata --syncer snowflake://syncer-overwrite.toml --config dogfood
            ```

[cs-tools-serverless]: ../../getting-started/#serverless
[syncer-manifest]: https://github.com/thoughtspot/cs_tools/blob/master/cs_tools/sync/snowflake/MANIFEST.json
[snowflake-account-id]: https://docs.snowflake.com/en/user-guide/admin-account-identifier
[snowflake-auth]: https://docs.snowflake.com/en/developer-guide/node-js/nodejs-driver-authenticate