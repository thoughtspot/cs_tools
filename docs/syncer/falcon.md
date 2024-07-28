---
icon: material/database
hide:
  - toc
---

Falcon is __ThoughtSpot__'s proprietary in-memory database that exists as part of your cluster. Its speed allowed our users to be able to analyze along any dimension without there being any time penalty, giving them a free reign to do any kind of analysis. This data store has been the backbone of many of our long-term customers.

<span class='fc-coral'>__This database is only available for data insertion if you operate on the Software version of the product__</span>, and are not using Embrace Connections to a cloud-native data store.

!!! note "Falcon parameters"

    ### __Required__ parameters are in __red__{ .fc-red } and __Optional__ parameters are in __blue__{ .fc-blue }.
    
    ---

    - [X] __database__{ .fc-red }, _the database to write new data to_
    <br />___if the database or tables do not exist in the database.schema location already, we'll auto-create them___{ .fc-green }
    
    ---
    
    - [ ] __schema__{ .fc-blue }, _the schema to write new data to_
    <br />___if the schema or tables do not exist in the database.schema location already, we'll auto-create them___{ .fc-green }
    <br />__default__{ .fc-gray }: `falcon_default_schema`

    ---

    - [ ] __wait_for_dataload_completion__{ .fc-blue }, _pause after loading data to check if it was successful_
    <br />__default__{ .fc-gray }: `false` ( __allowed__{ .fc-green }: `true`, `false` )

    ---

    - [ ] __ignore_load_balancer_redirect__{ .fc-blue }, _whether or not to redirect from the serving node_
    <br />__default__{ .fc-gray }: `false` ( __allowed__{ .fc-green }: `true`, `false` )

    ---

    - [ ] __load_strategy__{ .fc-blue}, _how to write new data into existing tables_
    <br />__default__{ .fc-gray }: `APPEND` ( __allowed__{ .fc-green }: `APPEND`, `TRUNCATE`, `UPSERT` )


??? question "How do I use the Falcon syncer in commands?"

    `cs_tools tools searchable bi-server --syncer falcon://database=cs_tools`

    __- or -__{ .fc-blue }

    `cs_tools tools searchable bi-server --syncer falcon://definition.toml`


## Definition TOML Example

`definition.toml`
```toml
[configuration]
database = "cs_tools"
load_strategy = "append"
```
