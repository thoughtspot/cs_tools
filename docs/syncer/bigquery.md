---
icon: material/database
hide:
  - toc
---

__BigQuery__ is a serverless, cost-effective and multicloud data warehouse designed to help you turn big data into valuable business insights. It a fully-managed, serverless data warehouse that enables scalable analysis over petabytes of data.

<span class=fc-red>__In order to use the BigQuery syncer__</span>, you must first configure your local environment. Click the __setup instructions__{ .fc-purple } below.

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
    
    __[optional]__{ .fc-purple }
    <br/>:fontawesome-brands-apple:, :fontawesome-brands-linux: Move the downloaded file to `~/.config/cs_tools/bigquery/credentials.json`.
    <br/>:fontawesome-brands-windows: Move the downloaded file to `%APPDATA%\cs_tools\bigquery\credentials.json`.


!!! note "BigQuery parameters"

    ### __Required__ parameters are in __red__{ .fc-red } and __Optional__ parameters are in __blue__{ .fc-blue }.
    
    ---

    - [X] __project_id__{ .fc-red }, _your BigQuery [__project identifier__][gc-project-id]_

    ---

    - [X] __dataset__{ .fc-red }, _the dataset to write new data to_
    <br />___if tables do not exist in the project.dataset location already, we'll auto-create them___{ .fc-green }

    ---

    - [X] __credentials_keyfile__{ .fc-red }, _the path to your credentials JSON_

    ---

    - [ ] __load_strategy__{ .fc-blue}, _how to write new data into existing tables_
    <br />__default__{ .fc-gray }: `APPEND` ( __allowed__{ .fc-green }: `APPEND`, `TRUNCATE`, `UPSERT` )


??? question "How do I use the BigQuery syncer in commands?"

    `cs_tools tools searchable bi-server --syncer bigquery://project_id=cs_tools&dataset=cs_tools_v150&credentials_keyfile=/usr/etc/searchable-ef192fec85db.json`

    __- or -__{ .fc-blue }

    `cs_tools tools searchable bi-server --syncer bigquery://definition.toml`


## Definition TOML Example

`definition.toml`
```toml
[configuration]
project_id = "cs_tools"
dataset = "cs_tools_v150"
credentials_keyfile = "/usr/etc/searchable-ef192fec85db.json"
load_strategy = 'truncate'
```

[gc-dev-console]: https://console.cloud.google.com/apis/dashboard
[gc-service-account]: https://cloud.google.com/docs/authentication/getting-started#creating_a_service_account
[gc-project-id]: https://support.google.com/googleapi/answer/7014113?hl=en
