---
icon: material/database
hide:
  - toc
---

!!! note "Parameters"

    ### __Required__ parameters are in __red__{ .fc-red } and __Optional__ parameters are in __blue__{ .fc-blue }.
    
    ---

    - [X] __host__{ .fc-red }, *the IP address or URL of your Trino catalog*

    ---

    - [ ] __port__{ .fc-blue }, *the port number where your Trino catalog is located*
    <br />__default__{ .fc-gray }: `8080`

    ---

    - [X] __catalog__{ .fc-red }, *the catalog to write new data to*
    <br />*__if tables do not exist in the__ `catalog.schema` __location already, we'll auto-create them__*{ .fc-green }

    ---

    - [ ] __schema__{ .fc-blue }, *the schema to write new data to*
    <br />__default__{ .fc-gray }: `public`, *__if tables do not exist in the__ `catalog.schema` __location already, we'll auto-create them__*{ .fc-green }

    ---

    - [X] __authentication__{ .fc-red }, *the type of authentication mechanism to use to connect to Trino*
    <br />( __allowed__{ .fc-green }: `basic`, `jwt` )

    ---

    - [X] __username__{ .fc-red }, *your Trino username*

    ---

    - [X] __secret__{ .fc-red }, *the secret value to pass to the authentication mechanism*
    <br />*__this will be either a <span class=fc-purple>password</span> or <span class=fc-purple>jwt</span>__*{ .fc-green }

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
        cs_tools tools searchable metadata --syncer "trino://host=coordinator.thoughtspot.com&catalog=thoughtspot&schema=cs_tools&authentication=basic&username=tsadmin&secret=[redacted]" --config dogfood
        ```

        <sup class=fc-gray><i>* when declaring multiple parameters inline, you should <b class=fc-purple>wrap the enter value</b> in quotes.</i></sup>

    === ":recycle: &nbsp; Configuration File"

        1. Create a file with `.toml` extension.

            ??? abstract "syncer-overwrite.toml"
                ```toml
                [configuration]
                host = "coordinator.thoughtspot.com"
                port = 8080
                catalog = "thoughtspot"
                schema = "cs_tools"
                authentication = "basic"
                username = "tsadmin"
                secret = "[redacted]"
                load_strategy = "TRUNCATE"
                ```
                <sup class=fc-gray><i>* this is a complete example, not all parameters are <b class=fc-red>required</b>.</i></sup>

        2. Reference the filename in your command in place of the parameters.

            ```bash
            cs_tools tools searchable metadata --syncer trino://syncer-overwrite.toml --config dogfood
            ```

[cs-tools-serverless]: ../../getting-started/#__tabbed_1_4
[syncer-manifest]: https://github.com/thoughtspot/cs_tools/blob/master/cs_tools/sync/starburst/MANIFEST.json