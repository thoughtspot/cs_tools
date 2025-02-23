---
icon: material/database
hide:
  - toc
---

??? tinm "There is No Magic!"

    __This database is only available if you host the Software version of the ThoughtSpot product__{ .fc-purple }, and are not using [__Connections__][ts-sw-connections] to an external data store.


!!! note "Parameters"

    ### __Required__ parameters are in __red__{ .fc-red } and __Optional__ parameters are in __blue__{ .fc-blue }.
    
    ---

    - [X] __database__{ .fc-red }, *the database to write new data to*
    <br />*__if the database or tables do not exist in the__ `database.schema` __location already, we'll auto-create them__*{ .fc-green }
    
    ---
    
    - [ ] __schema__{ .fc-blue }, _the schema to write new data to_
    <br />*__if the schema or tables do not exist in the__ `database.schema` __location already, we'll auto-create them__*{ .fc-green }
    <br />__default__{ .fc-gray }: `falcon_default_schema`

    ---

    - [ ] __wait_for_dataload_completion__{ .fc-blue }, *pause after loading data to check if it was successful*
    <br />__default__{ .fc-gray }: `false` ( __allowed__{ .fc-green }: `true`, `false` )

    ---

    - [ ] __ignore_load_balancer_redirect__{ .fc-blue }, *whether or not to redirect from the serving node*
    <br />__default__{ .fc-gray }: `false` ( __allowed__{ .fc-green }: `true`, `false` )

    ---

    - [ ] __load_strategy__{ .fc-blue}, *how to write new data into existing tables*
    <br />__default__{ .fc-gray }: `APPEND` ( __allowed__{ .fc-green }: `APPEND`, `TRUNCATE`, `UPSERT` )


??? question "How do I use the Syncer in commands?"

    __CS Tools__ accepts syncer definitions in either declarative or configuration file form.

    <sub class=fc-blue>Find the copy button :material-content-copy: to the right of the code block.</sub>

    === ":mega: &nbsp; Declarative"

        Simply write the parameters out alongside the command.

        ```bash
        cs_tools tools searchable metadata --syncer "falcon://database=cs_tools" --config dogfood
        ```

        <sup class=fc-gray><i>* when declaring multiple parameters inline, you should <b class=fc-purple>wrap the enter value</b> in quotes.</i></sup>

    === ":recycle: &nbsp; Configuration File"

        1. Create a file with the `.toml` extension.

            ??? abstract "syncer-overwrite.toml"
                ```toml
                [configuration]
                database = "cs_tools"
                schema = "falcon_default_schema"
                wait_for_dataload_completion = true
                ignore_load_balancer_redirect = false
                load_strategy = "TRUNCATE"
                ```
                <sup class=fc-gray><i>* this is a complete example, not all parameters are <b class=fc-red>required</b>.</i></sup>

        2. Write the filename in your command in place of the parameters.

            ```bash
            cs_tools tools searchable metadata --syncer falcon://syncer-overwrite.toml --config dogfood
            ```

[ts-sw-connections]: https://docs.thoughtspot.com/software/latest/connections