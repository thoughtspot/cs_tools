---
hide:
  - toc
---

<style>
    .task-list-item { color: var(--ts-color-black60); }
</style>

__CS Tools__ interacts with your __ThoughtSpot__ cluster through the [__V2.0 REST APIs__][ts-rest-apis]. Oftentimes the data that comes back from an API cannot exposed directly back to analytics tools like __ThoughtSpot__, __because it's in the wrong shape__{ .fc-red }. Additionally, __ThoughtSpot__ requires that your data be stored in a database in order to ask questions of it.

  - [x] __CS Tools__ takes the responsibility of reshaping that data into a tabular format
  - [x] __Syncers__{ .fc-purple } abstract the details of how to read and write from popular tabular data formats.

We've implemented __Syncers__{ .fc-purple } to many popular data stores, including many of the [__Connection types__][ts-cl-connections] that __ThoughtSpot__ supports.

---

![syncer-architecture](../../assets/images/syncer-architecture.svg)

---

## __How do I use Syncers?__ { .fc-blue }

__All__ __Syncers__{ .fc-purple } __require configuration.__

__CS Tools__ commands which support interacting with data stores will provide a `--syncer` parameter.

The value you pass to it will look similar to a URL you would type in your browser.

!!! abstract ""

    === "Protocol"
        The dialect of the data store you want to interact with.
        ```bash
        cs_tools tools searchable metadata --syncer "{==sqlite==}://database_path=thoughtspot.db"
        ```
    === "Separator"
        It.. separates :sweat_smile:
        ```bash
        cs_tools tools searchable metadata --syncer "sqlite{==://==}database_path=thoughtspot.db"
        ```
    === "Parameters (Declarative :mega:)"
        The configuration information in order to interact with the data stores.
        ```bash
        cs_tools tools searchable metadata --syncer "sqlite://{==database_path=thoughtspot.db==}"
        ```
    === "Parameters (Configuration :recycle:)"
        The configuration information in order to interact with the data stores.
        ```bash
        cs_tools tools searchable metadata --syncer "sqlite://{==syncer-overwrite.toml==}"
        ```

!!! question "How do I use the Syncer in commands?"

    __CS Tools__ accepts syncer definitions in either declarative or configuration file form.

    <sub class=fc-blue>Find the copy button :material-content-copy: to the right of the code block.</sub>

    === ":fontawesome-solid-file-csv: &nbsp; CSV"
        === ":mega: &nbsp; Declarative"

            Simply write the parameters out alongside the command.

            ```bash
            cs_tools tools searchable metadata --syncer "csv://directory=.&delimiter=|" --config dogfood
            ```

            <sup class=fc-gray><i>* when declaring multiple parameters inline, you should <b class=fc-purple>wrap the enter value</b> in quotes.</i></sup>

        === ":recycle: &nbsp; Configuration File"

            1. Create a file with the `.toml` extension.

                ??? abstract "syncer-overwrite.toml"
                    ```toml
                    [configuration]
                    directory = "."
                    delimiter = "|"
                    escape_character = "\\"
                    empty_as_null = true
                    quoting = "ALL"
                    date_time_format = "%Y-%m-%dT%H:%M:%S%z"
                    header = false
                    save_strategy = "APPEND"
                    ```
                    <sup class=fc-gray><i>* this is a complete example, not all parameters are <b class=fc-red>required</b>.</i></sup>

            2. Write the filename in your command in place of the parameters.

                ```bash
                cs_tools tools searchable metadata --syncer csv://syncer-overwrite.toml --config dogfood
                ```

    === ":material-microsoft-excel: &nbsp; Excel"
        === ":mega: &nbsp; Declarative"

            Simply write the parameters out alongside the command.

            ```bash
            cs_tools tools searchable metadata --syncer "excel://filepath=searchable.xlsx" --config dogfood
            ```

            <sup class=fc-gray><i>* when declaring multiple parameters inline, you should <b class=fc-purple>wrap the enter value</b> in quotes.</i></sup>

        === ":recycle: &nbsp; Configuration File"

            1. Create a file with the `.toml` extension.

                ??? abstract "syncer-overwrite.toml"
                    ```toml
                    [configuration]
                    filepath = "searchable.xlsx"
                    filepath_suffix = "--generated-on-%Y-%m-%d"
                    date_time_format = "%Y-%m-%dT%H:%M:%S%z"
                    save_strategy = "OVERWRITE"
                    ```
                    <sup class=fc-gray><i>* this is a complete example, not all parameters are <b class=fc-red>required</b>.</i></sup>

            2. Write the filename in your command in place of the parameters.

                ```bash
                cs_tools tools searchable metadata --syncer excel://syncer-overwrite.toml --config dogfood
                ```

    === ":material-code-json: &nbsp; JSON"
        === ":mega: &nbsp; Declarative"

            Simply write the parameters out alongside the command.

            ```bash
            cs_tools tools searchable metadata --syncer "json://directory=." --config dogfood
            ```

            <sup class=fc-gray><i>* when declaring multiple parameters inline, you should <b class=fc-purple>wrap the enter value</b> in quotes.</i></sup>

        === ":recycle: &nbsp; Configuration File"

            1. Create a file with the `.toml` extension.

                ??? abstract "syncer-overwrite.toml"
                    ```toml
                    [configuration]
                    directory = "."
                    encoding = "UTF-8"
                    indentation = 2
                    ```
                    <sup class=fc-gray><i>* this is a complete example, not all parameters are <b class=fc-red>required</b>.</i></sup>

            2. Write the filename in your command in place of the parameters.

                ```bash
                cs_tools tools searchable metadata --syncer json://syncer-overwrite.toml --config dogfood
                ```

    === ":simple-sqlite: &nbsp; SQLite"
        === ":mega: &nbsp; Declarative"

            Simply write the parameters out alongside the command.

            ```bash
            cs_tools tools searchable metadata --syncer "sqlite://database_path=thoughtspot.db" --config dogfood
            ```

            <sup class=fc-gray><i>* when declaring multiple parameters inline, you should <b class=fc-purple>wrap the enter value</b> in quotes.</i></sup>

        === ":recycle: &nbsp; Configuration File"

            1. Create a file with the `.toml` extension.

                ??? abstract "syncer-overwrite.toml"
                    ```toml
                    [configuration]
                    database_path = "thoughtspot.db"
                    pragma_speedy_inserts = true
                    load_strategy = "TRUNCATE"
                    ```
                    <sup class=fc-gray><i>* this is a complete example, not all parameters are <b class=fc-red>required</b>.</i></sup>

            2. Write the filename in your command in place of the parameters.

                ```bash
                cs_tools tools searchable metadata --syncer sqlite://syncer-overwrite.toml --config dogfood
                ```

    === ":simple-snowflake: &nbsp; Snowflake"
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



[ts-rest-apis]: https://developers.thoughtspot.com/docs/rest-apiv2-reference
[ts-cl-connections]: https://docs.thoughtspot.com/cloud/latest/connections