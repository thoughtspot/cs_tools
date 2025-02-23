---
icon: material/database
hide:
  - toc
---

??? example "Setup instructions"

    1. Head to [Google Developers Console][gc-dev-console] and create a new project (or select the one you already have).
    2. Go to <span class=fc-blue>__APIs & Services > Enable APIs & services.__</span>
        - Click the button for <span class=fc-blue>__+ ENABLE APIS AND SERVICES__</span>
        - In the Search bar, find <span class=fc-blue>__BigQuery API__</span>. Click <span class=fc-blue>__ENABLE__</span>.
    3. Create a [^^Service Account^^][gc-service-account].
    4. Create a service account key.
        - In the Cloud Console, click the email address for the service account that you created.
        - Click <span class=fc-blue>__Keys__</span>.
        - Click <span class=fc-blue>__Add key__</span>, then click <span class=fc-blue>__Create new key__</span>.
        - Click <span class=fc-blue>__Create__</span>. A JSON key file is downloaded to your computer.
        - Click <span class=fc-blue>__Close__</span>.
    

!!! note "Parameters"

    ### __Required__ parameters are in __red__{ .fc-red } and __Optional__ parameters are in __blue__{ .fc-blue }.
    
    ---

    - [X] __project_id__{ .fc-red }, *your BigQuery [__project identifier__][gc-project-id]*

    ---

    - [X] __dataset__{ .fc-red }, *the dataset to write new data to*
    <br />*__if tables do not exist in the__ `project.dataset` __location already, we'll auto-create them__*{ .fc-green }

    ---

    - [X] __credentials_keyfile__{ .fc-red }, *the path to your credentials JSON*

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
        cs_tools tools searchable metadata --syncer "bigquery://project_id=thoughtspot&dataset=cs_tools&credentials_keyfile=/path/to/cs_tools/bigquery/credentials.json" --config dogfood
        ```

        <sup class=fc-gray><i>* when declaring multiple parameters inline, you should <b class=fc-purple>wrap the enter value</b> in quotes.</i></sup>

    === ":recycle: &nbsp; Configuration File"

        1. Create a file with `.toml` extension.

            ??? abstract "syncer-overwrite.toml"
                ```toml
                [configuration]
                project_id = "thoughtspot"
                dataset = "cs_tools"
                credentials_keyfile = "/path/to/cs_tools/bigquery/credentials.json"
                load_strategy = "TRUNCATE"
                ```
                <sup class=fc-gray><i>* this is a complete example, not all parameters are <b class=fc-red>required</b>.</i></sup>

        2. Reference the filename in your command in place of the parameters.

            ```bash
            cs_tools tools searchable metadata --syncer bigquery://syncer-overwrite.toml --config dogfood
            ```

[cs-tools-serverless]: ../../getting-started/#serverless
[syncer-manifest]: https://github.com/thoughtspot/cs_tools/blob/master/cs_tools/sync/bigquery/MANIFEST.json
[gc-dev-console]: https://console.cloud.google.com/apis/dashboard
[gc-service-account]: https://cloud.google.com/docs/authentication/getting-started#creating_a_service_account
[gc-project-id]: https://support.google.com/googleapi/answer/7014113?hl=en
