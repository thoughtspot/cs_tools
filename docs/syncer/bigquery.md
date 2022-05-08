---
hide:
  - toc
---

??? attention "In Beta"

    The Syncer protocol is in beta, it has been added to __CS Tools__ in v1.3 on a
    __provisional basis__. It may change significantly in future releases and its
    interface will not be concrete until v2.

    Feedback from the community while it's still provisional would be extremely useful;
    either comment on [#25][gh-issue25] or create a new issue.

__BigQuery__ is a serverless, cost-effective and multicloud data warehouse designed to help you turn big data into valuable business insights. It a fully-managed, serverless data warehouse that enables scalable analysis over petabytes of data.

<span class=fc-coral>__In order to use the BigQuery syncer__</span>, you must first configure your local environment. The setup instructions below will help you create a __Google Cloud Project__ and enable the __BigQuery Storage API__ to allow __CS Tools__ to interact with your BigQuery environment.

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


??? info "Want to see the source code?"
    
    *If you're writing a Custom Syncer, you can check our project code for an example.*

    [cs_tools/sync/__bigquery__/syncer.py][syncer.py]


## BigQuery `DEFINITION.toml` spec

> __project_id__{ .fc-blue }: id of your google cloud project

> __dataset__{ .fc-blue }: name of your bigquery dataset

> __credentials_file__{ .fc-blue }: <span class=fc-coral>optional</span>, absolute path to your credentials JSON file
<br/>*<span class=fc-mint>default</span>:* `<cs_tools-app-directory>/bigquery/credentials.json`
<br/>*you can find the cs_tools app directory by running `cs_tools config show`*

> __truncate_on_load__{ .fc-blue }: <span class=fc-coral>optional</span>, either `true` or `false`, remove all data in the table prior to a new data load
<br/>*<span class=fc-mint>default</span>:* `true`


??? question "How do I use the BigQuery syncer in commands?"

    === ":fontawesome-brands-apple: Mac, :fontawesome-brands-linux: Linux"

        `cs_tools tools searchable bi-server bigquery:///home/user/syncers/bigquery-definition.toml --compact`

        `cs_tools tools searchable bi-server bigquery://default --compact`

    === ":fontawesome-brands-windows: Windows"

        `cs_tools tools searchable bi-server bigquery://C:\Users\%USERNAME%\Downloads\bigquery-definition.toml --compact`

        `cs_tools tools searchable bi-server bigquery://default --compact`

    *Learn how to register a default for syncers in [How-to: Setup a Configuration File][how-to-config].*


## Full Definition Example

`definition.toml`
```toml
[configuration]
project_id = 'cs_tools'
dataset = 'thoughtspot'
credentials_file = 'C:\Users\NameyNamerson\Downloads\syncers\<project-name>.json'
truncate_on_load = true
```

[gh-issue25]: https://github.com/thoughtspot/cs_tools/issues/25
[syncer.py]: https://github.com/thoughtspot/cs_tools/blob/master/cs_tools/sync/bigquery/syncer.py
[gc-dev-console]: https://console.cloud.google.com/apis/dashboard
[gc-service-account]: https://cloud.google.com/docs/authentication/getting-started#creating_a_service_account
[how-to-config]: ../how-to/configuration-file.md
