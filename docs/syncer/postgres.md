---
icon: material/database
hide:
  - toc
---

??? tinm "There is No Magic!"

    __This Syncer uses the highly popular [psycopg project][pg-psyco] under the hood__.
    
    This means the syncer should transparently support any pg dialect (eg. [Amazon RDS][pg-rds], [Amazon Aurora][pg-aurora], [Google Cloud SQL][pg-cloudsql], [CockroachDB][pg-cockroach] in pg mode, etc.)


!!! note "Parameters"

    ### __Required__ parameters are in __red__{ .fc-red } and __Optional__ parameters are in __blue__{ .fc-blue }.
    
    ---

    - [X] __host__{ .fc-red }, *the IP address or URL of your postgres cluster*

    ---

    - [ ] __port__{ .fc-blue}, *how to write new data into existing tables*
    <br />__default__{ .fc-gray }: `5432`

    ---

    - [X] __database__{ .fc-red }, *the database to write new data to*
    <br />*__if tables do not exist in the__ `database.schema` __location already, we'll auto-create them__*{ .fc-green }

    ---

    - [ ] __schema__{ .fc-blue }, _the schema to write new data to_
    <br />__default__{ .fc-gray }: `public`
    <br />*__if tables do not exist in the__ `database.schema` __location already, we'll auto-create them__*{ .fc-green }

    ---

    - [X] __username__{ .fc-red }, *your Snowflake username*
    
    ---

    - [ ] __secret__{ .fc-blue }, _the secret value to pass to the authentication mechanism_
    <br />*this will be your __password__{ .fc-purple }*
    
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
        cs_tools tools searchable metadata --syncer "postgres://host=pgdb-internal.company.com&database=thoughtspot&username=tsadmin" --config dogfood
        ```

        <sup class=fc-gray><i>* when declaring multiple parameters inline, you should <b class=fc-purple>wrap the enter value</b> in quotes.</i></sup>

    === ":recycle: &nbsp; Configuration File"

        1. Create a file with the `.toml` extension.

            ??? abstract "syncer-overwrite.toml"
                ```toml
                [configuration]
                host = "pgdb-internal.company.com"
                port = 5432
                database = "thoughtspot"
                schema = "cs_tools"
                username = "tsadmin"
                secret = "[redacted]"
                load_strategy = "TRUNCATE"
                ```
                <sup class=fc-gray><i>* this is a complete example, not all parameters are <b class=fc-red>required</b>.</i></sup>

        2. Write the filename in your command in place of the parameters.

            ```bash
            cs_tools tools searchable metadata --syncer postgres://syncer-overwrite.toml --config dogfood
            ```

[cs-tools-serverless]: ../../getting-started/#__tabbed_1_4
[syncer-manifest]: https://github.com/thoughtspot/cs_tools/blob/master/cs_tools/sync/databricks/MANIFEST.json
[pg-psyco]: https://www.psycopg.org
[pg-rds]: https://aws.amazon.com/rds/
[pg-aurora]: https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/Aurora.AuroraPostgreSQL.html
[pg-cloudsql]: https://cloud.google.com/sql/postgresql?hl=en
[pg-cockroach]: https://www.cockroachlabs.com/docs/stable/postgresql-compatibility