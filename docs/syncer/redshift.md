---
icon: material/database
hide:
  - toc
---

??? example "Setup instructions"

    __Your Redshift cluster must be accessible over the internet.__{ .fc-purple }
    
    Learn how to make your cluster accessible in the [__Redshift documentation__](https://repost.aws/knowledge-center/redshift-cluster-private-public).


!!! note "Parameters"

    ### __Required__ parameters are in __red__{ .fc-red } and __Optional__ parameters are in __blue__{ .fc-blue }.
    
    ---

    - [X] __host__{ .fc-red }, *the URL of your Redshift database*

    ---

    - [ ] __port__{ .fc-blue }, *the port number where your Redshift database is located*
    <br />__default__{ .fc-gray }: `5439`

    ---

    - [X] __database__{ .fc-red }, *the database to write new data to*
    <br />*__if tables do not exist in the__ `database` __location already, we'll auto-create them__*{ .fc-green }

    ---

    - [X] __username__{ .fc-red }, *your Redshift username*

    ---

    - [X] __secret__{ .fc-red }, *the secret value to pass to the authentication mechanism*
    <br />*this will be your __password__{ .fc-purple }*

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
        cs_tools tools searchable metadata --syncer "redshift://host=mycluster.abc123xyz789.us-west-2.redshift.amazonaws.com&port=5439&database=thoughtspot&username=tsadmin&secret=[redacted]" --config dogfood
        ```

        <sup class=fc-gray><i>* when declaring multiple parameters inline, you should <b class=fc-purple>wrap the enter value</b> in quotes.</i></sup>

    === ":recycle: &nbsp; Configuration File"

        1. Create a file with `.toml` extension.

            ??? abstract "syncer-overwrite.toml"
                ```toml
                [configuration]
                host = "mycluster.abc123xyz789.us-west-2.redshift.amazonaws.com"
                port = 5439
                database = "thoughtspot"
                username = "tsadmin"
                secret = "[redacted]"
                load_strategy = "TRUNCATE"
                ```
                <sup class=fc-gray><i>* this is a complete example, not all parameters are <b class=fc-red>required</b>.</i></sup>

        2. Reference the filename in your command in place of the parameters.

            ```bash
            cs_tools tools searchable metadata --syncer redshift://syncer-overwrite.toml --config dogfood
            ```

[cs-tools-serverless]: ../../getting-started/#serverless
[syncer-manifest]: https://github.com/thoughtspot/cs_tools/blob/master/cs_tools/sync/redshift/MANIFEST.json
