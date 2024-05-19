---
icon: material/database
hide:
  - toc
---

__PostgreSQL__ is a powerful open-source relational database management system. It provides a rich set of data types, operators, and functions to work with structured and semi-structured data.

!!! note "Postgres parameters"

    ### __Required__ parameters are in __red__{ .fc-red } and __Optional__ parameters are in __blue__{ .fc-blue }.
    
    ---

    - [X] __host__{ .fc-red }, _the IP address or URL of your postgres cluster_

    ---

    - [ ] __port__{ .fc-blue}, _how to write new data into existing tables_
    <br />__default__{ .fc-gray }: `5432`

    ---

    - [X] __database__{ .fc-red }, _the database to write new data to_
    <br />___if tables do not exist in the project.dataset location already, we'll auto-create them___{ .fc-green }

    ---

    - [ ] __schema__{ .fc-blue }, _the schema to write new data to_
    <br />__default__{ .fc-gray }: `public`
    <br />___if tables do not exist in the project.dataset location already, we'll auto-create them___{ .fc-green }

    ---

    - [X] __username__{ .fc-red }, _your Snowflake username_
    
    ---

    - [ ] __secret__{ .fc-blue }, _the secret value to pass to the authentication mechanism_
    <br />_this will be your __password__{ .fc-purple }_
    
    ---

    - [ ] __load_strategy__{ .fc-blue}, _how to write new data into existing tables_
    <br />__default__{ .fc-gray }: `APPEND` ( __allowed__{ .fc-green }: `APPEND`, `TRUNCATE`, `UPSERT` )


??? question "How do I use the Postgres syncer in commands?"

    `cs_tools tools searchable bi-server --syncer postgres://host=192.168.1.25&username=postgres&database=cs_tools`

    __- or -__{ .fc-blue }

    `cs_tools tools searchable bi-server --syncer postgres://definition.toml`


## Definition TOML Example

`definition.toml`
```toml
[configuration]
host = "192.168.1.25"
username = "postgres"
secret = "..."
database = "cs_tools"
load_strategy = 'truncate'
```

[gc-dev-console]: https://console.cloud.google.com/apis/dashboard
[gc-service-account]: https://cloud.google.com/docs/authentication/getting-started#creating_a_service_account
[gc-project-id]: https://support.google.com/googleapi/answer/7014113?hl=en
