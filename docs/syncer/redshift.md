---
icon: material/database
hide:
  - toc
---

Redshift is a powerful data warehousing service provided by Amazon Web Services (AWS). It's designed to help businesses quickly analyze large amounts of data.

Redshift's combination of high performance, scalability, cost-effectiveness, ease of use, and advanced analytics capabilities make it a highly useful data warehousing solution for businesses of all sizes, especially those dealing with large and growing datasets.

??? example "Setup instructions"

    If you face issues with connectivity to your Redshift cluster, make sure you can first access the cluster from your local machine.

    You can learn how to make your cluster accessible in the [__Redshift documentation__](https://repost.aws/knowledge-center/redshift-cluster-private-public).


!!! note "Redshift parameters"

    ### __Required__ parameters are in __red__{ .fc-red } and __Optional__ parameters are in __blue__{ .fc-blue }.
    
    ---

    - [X] __host__{ .fc-red }, _the URL of your Redshift database_

    ---

    - [ ] __port__{ .fc-blue }, _the port number where your Redshift database is located_
    <br />__default__{ .fc-gray }: `5439`

    ---

    - [X] __database__{ .fc-red }, _the database to write new data to_
    <br />___if tables do not exist in the database location already, we'll auto-create them___{ .fc-green }

    ---

    - [X] __authentication__{ .fc-red }, _the type of authentication mechanism to use to connect to Redshift_
    <br />( __allowed__{ .fc-green }: `basic` )

    ---

    - [X] __username__{ .fc-red }, _your Redshift username_

    ---

    - [X] __secret__{ .fc-red }, _the secret value to pass to the authentication mechanism_
    <br />_this will be your __password__{ .fc-purple }_

    ---

    - [ ] __load_strategy__{ .fc-blue}, _how to write new data into existing tables_
    <br />__default__{ .fc-gray }: `APPEND` ( __allowed__{ .fc-green }: `APPEND`, `TRUNCATE`, `UPSERT` )


??? question "How do I use the Redshift syncer in commands?"

    `cs_tools tools searchable bi-server --syncer redshift://host=0.0.0.0&database=...&username=admin&password=...&load_strategy=upsert`

    __- or -__{ .fc-blue }

    `cs_tools tools searchable bi-server --syncer redshift://definition.toml`


## Definition TOML Example

`definition.toml`
```toml
[configuration]
host = "mycluster.us0I3nrnge4i.us-west-2.redshift.amazonaws.com"
database = "..."
username = "admin"
secret = "..."
load_strategy = "upsert"
```
