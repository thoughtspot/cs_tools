---
hide:
  - navigation
---

# Searchable

Use __ThoughtSpot__, on __ThoughtSpot__!

??? tinm "There is No Magic!"

    Remember, __CS Tools__ wraps the __ThoughtSpot__ [__REST APIs__][ts-rest-v2]. This tool uses the following endpoints.

    - [`/orgs/search`][ts-rest-orgs-search] *for fetching Org info*{ .fc-gray }
    - [`/groups/search`][ts-rest-groups-search] *for fetching Group info, assigned Privileges, as well as their Group Memberships*{ .fc-gray }
    - [`/users/search`][ts-rest-users-search] *for fetching User info, as well as their Org and Group Memberships*{ .fc-gray }
    - [`/tags/search`][ts-rest-tags-search] *for fetching Tag info*{ .fc-gray }
    - [`/metadata/search`][ts-rest-metadata-search] *for fetching Connection, Table, Model, Column, Answer, and Liveboard info, as well as their tags*{ .fc-gray }
    - [`/metadata/search`][ts-rest-metadata-search] *for fetching Column details, Synonyms, even on hidden columns*{ .fc-gray }
    - [`/metadata/search`][ts-rest-metadata-search] *for fetching Dependents based on all available columns*{ .fc-gray }
    - [`/security/metadata/fetch-permissions`][ts-rest-metadata-security] *for fetching Sharing access controls on all available metadata*{ .fc-gray }
    - [`/searchdata`][ts-rest-searchdata] *for extracting the __TS: BI Server__ Model*{ .fc-gray }
    - [`/logs/fetch`][ts-rest-audit-logs] *for extracting the __Audit Logs__ data feed*{ .fc-gray }
    - [`/metadata/tml/export`][ts-rest-metadata-tml-export] *for extracting the TML representation of metadata*{ .fc-gray }
    - [`/metadata/tml/import`][ts-rest-metadata-tml-import] *for deploying the Searchable SpotApp to your __ThoughtSpot__ cluster*{ .fc-gray }

!!! tip ""

    === "--help"
        ??? abstract "Get the Command"
            ```shell
            cs_tools tools searchable --help
            ```
        ~cs~tools tools searchable --help
    === "metadata"
        ??? abstract "Get the Command"
            ```shell
            cs_tools tools searchable metadata --help
            ```
        ~cs~tools tools searchable metadata --help
    === "bi-server"
        ??? abstract "Get the Command"
            ```shell
            cs_tools tools searchable bi-server --help
            ```
        ~cs~tools tools searchable bi-server --help
    === "audit-logs"
        ??? abstract "Get the Command"
            ```shell
            cs_tools tools searchable audit-logs --help
            ```
        ~cs~tools tools searchable audit-logs --help
    === "tml"
        ??? abstract "Get the Command"
            ```shell
            cs_tools tools searchable tml --help
            ```
        ~cs~tools tools searchable tml --help

---

### What's in the SpotApp?

You can find the [__raw TML in GitHub__][gh-searchable-tml], the entire package contains..

  - All Tables which are [__Modeled for Search__][tsa-mfs]
  - A starter Model focused on __User Adoption__{ .fc-green }
  - A starter Model focused on __Metadata Lineage__{ .fc-purple }
  - A __BETA__{ .fc-blue } starter Model for __Audit Events__
  - A __BETA__{ .fc-blue } starter Model for __Metadata Snapshots__

!!! tip ""

    === "Worksheet Column Utilization"
        __Learn about how your Worksheets are being used! Here's some questions you can answer with this new Worksheet and Liveboard combo.__{ .fc-purple }

        - What's the breakdown of columns in your Worksheet?
        - Are there any columns which aren't seeing any use?
        - Have you exposed any Hidden columns, which are unintentionally locking dependencies?
        - Come to think of it, _just how many dependencies_ are there on this Worksheet?
        - Who is creating content that's being heavily used by others?

        === "Overview"
            <img src="../../changelog/v1_5_0/worksheet_column_utilization_overview.png">
        === "Dependencies"
            <img src="../../changelog/v1_5_0/worksheet_column_utilization_dependencies.png">
        === "Influencers"
            <img src="../../changelog/v1_5_0/worksheet_column_utilization_influencers.png">

    === "TS BI Server Advanced"
        __Learn about how well your Cluster is being adopted! Here's some questions you can answer with this new Worksheet and Liveboard combo.__{ .fc-purple }

        - When do Users log in and interact with ThoughtSpot?
        - What does my Month Active Users look like on Mobile? How about for Search?
        - How many Users are losing or re-engaging on the platform?
        - What does query latency look like in ThoughtSpot? Is anyone having a poor experience?
        - Which Groups contribute the most activity in ThoughtSpot?

        === "Overview"
            <img src="../../changelog/v1_5_0/thoughtspot_adoption_overview.png">
        === "Adoption"
            <img src="../../changelog/v1_5_0/thoughtspot_adoption_adoption.png">
        === "Health"
            <img src="../../changelog/v1_5_0/thoughtspot_adoption_health.png">
        === "Archiver"
            <img src="../../changelog/v1_5_0/thoughtspot_adoption_archiver.png">
        === "Groups"
            <img src="../../changelog/v1_5_0/thoughtspot_adoption_groups.png">

---

### Gather Metadata

Most of the "data" that lives in your __ThoughtSpot__ cluster is data *__about your data__*. This changes every day as
users build, edit, and delete Models, Answers, and Liveboards in the system.

To get a complete view of your __Metadata__, you will need to run this command __on a regular basis__{ .fc-green }.

!!! tip "Syncer Load Strategy: TRUNCATE"
    Since this metadata is a snapshot at the time of running, it is best to use the __Syncer__ `load_strategy=TRUNCATE` for this command.

<sub>
  <b class=fc-purple>Haven't learned about Syncers yet?</b> <span class=fc-gray>Head on over to the
  [Syncer docs][syncer-base] to figure out how to store your __ThoughtSpot__ metadata in an external data store.
</sub>

!!! tip ""
    ??? abstract "Get the Command"
        ```shell
        cs_tools tools searchable metadata --help
        ```
    ~cs~tools tools searchable metadata --help

??? tinm "There is No Magic!"

    The __ThoughtSpot__ team runs this command on a daily cadence. You can find it here in our [__GitHub Actions__](https://github.com/thoughtspot/cs_tools/actions/workflows/fetch-metdata.yaml) and [__Workflow File__](https://github.com/thoughtspot/cs_tools/blob/6a8e43bba3140371109e79ef2de7309b7d2a21e5/.github/workflows/fetch-metdata.yaml#L63-L68).

---

### Mirror TS: BI Server

The central `FACT` table in the __Searcahble SpotApp__ is actually one that lives inside your __Thoughtspot__ platform
already! However, since __Thoughtspot__ does not allow relationships across Connections, we will need to copy that data
into our own database first.

__TS: BI Server__ is a User Activity history table, telling Administrators about actions a user takes while logged in to the system. 

To get a complete view of your __User Activity__, you will need to run this command __on a regular basis__{ .fc-green }.

!!! tip "Syncer Load Strategy: UPSERT"
    Since this is actual activity data, it is best to use the __Syncer__ `load_strategy=UPSERT` for this command.

<sub>
  <b class=fc-purple>Customers often schedule this command more often than their data pull window.</b>
  <span class=fc-gray>(eg. if you schedule daily, run for the last 7 days!)</span>
</sub>

!!! tip ""
    ??? abstract "Get the Command"
        ```shell
        cs_tools tools searchable bi-server --help
        ```
    ~cs~tools tools searchable bi-server --help

??? tinm "There is No Magic!"

    The __ThoughtSpot__ team runs this command on a daily cadence. You can find it here in our [__GitHub Actions__](https://github.com/thoughtspot/cs_tools/actions/workflows/fetch-bi-server.yaml) and [__Workflow File__](https://github.com/thoughtspot/cs_tools/blob/6a8e43bba3140371109e79ef2de7309b7d2a21e5/.github/workflows/fetch-bi-data.yaml#L70-L77).

---

### Deploy Searchable SpotApp

Once you're regularly extracting the __Metadata__ and __BI Server__, you are ready to deploy the __Searchable SpotApp__!

??? note "Should I use a new connection?"
    It's recommended to __use a separate Connection__{ .fc-purple } for the __CS Tools__ Searchable tables, even if
    you're combining them with your own business data. This is primarily so the __ThoughtSpot__ metadata is scoped
    separately from data your users would actually interact with.

This command will ask for some details about which Connection can access the __CS Tools__ tables created by your Syncer.
This are normal __ThoughtSpot__ fundamentals -- you just need to know your Connection GUID, and the name of the external
database (or catalog) and schema of where the Searchable data lives.

__You should only need to run this command once!__{ .fc-purple }

!!! tip ""
    ??? abstract "Get the Command"
        ```shell
        cs_tools tools searchable deploy --help
        ```
    ~cs~tools tools searchable deploy --help

---

### Optional: Extract Audit Logs

While __TS: BI Server__ is all about how Users interact with the system, it is also possible to extract __Audit Logs__.
These logs record all the security actions and changes made to objects on your __ThoughtSpot__ platform. Any time an
object is created, updated, deleted, or their access controls change, the Audit Logs will capture and record the event.

__This dataset is very "noisy" and produces a lot of data!__{ .fc-red }

<sup class=fc-gray>The lifetime of this dataset is only 30-45 rolling days of data, depending on the size of your cluster.</sup>

To get a complete view of your __Logs__, you will need to run this command __on a regular basis__{ .fc-green }.

!!! tip "Syncer Load Strategy: UPSERT"
    Since this actual log data, it is best to use the __Syncer__ `load_strategy=UPSERT` for this command.

<sub>
  <b class=fc-purple>Customers often schedule this command more often than their data pull window.</b>
  <span class=fc-gray>(eg. if you schedule daily, run for the last 7 days!)</span>
</sub>

!!! tip ""
    ??? abstract "Get the Command"
        ```shell
        cs_tools tools searchable audit-logs --help
        ```
    ~cs~tools tools searchable audit-logs --help

??? tinm "There is No Magic!"

    The __ThoughtSpot__ team runs this command on a daily cadence. You can find it here in our [__GitHub Actions__](https://github.com/thoughtspot/cs_tools/actions/workflows/fetch-audit-logs.yaml) and [__Workflow File__](https://github.com/thoughtspot/cs_tools/blob/6a8e43bba3140371109e79ef2de7309b7d2a21e5/.github/workflows/fetch-audit-logs.yaml#L64-L70).

---

### Optional: Extract TML Snapshots

The `metadata` commands provides a __LOT__ of data, and not all of it is used by the __Searchable SpotApp__ yet. Still,
many customers have asked about other properties of objects over the years. __TML__ is a the derived representation of
all user-facing objects in the system. Nearly every setting available on objects is captured within the __ThoughtSpot
Modeling Language__.

??? bug "With great power comes great ... work effort"

    __This is for advanced users only!__{ .fc-red }

    This command gives you the ability to export the TML of your objects as JSON, and store it in your database. From
    here, you can use JSON queries to pull out the data you need and join it back to the larger data models.

    - What Tables have RLS defined on them?
    - How many Vizualization on Liveboards have user-defined Formulas?
    - What is the formula expression used on my Models?
    - How many Users are engaging `vs` or `in` subqueries on their Searches?
    - What's the percentage of visualizations that are in `display_mode: TABLE_MODE`?

    All of these can be answered with the __TML__!

To get a complete view of __TML snapshots__, you will need to run this command __on a regular basis__{ .fc-green }.

!!! tip "Syncer Load Strategy: UPSERT"
    This table has a `snapshot_date` and defaults to tracking edits, it is best to use the __Syncer__ `load_strategy=UPSERT` for this command.

<sub>
  <b class=fc-purple>Customers often schedule this command more often than their data pull window.</b>
  <span class=fc-gray>(eg. if you schedule daily, run for the last 7 days!)</span>
</sub>

!!! tip ""
    ??? abstract "Get the Command"
        ```shell
        cs_tools tools searchable tml --help
        ```
    ~cs~tools tools searchable tml --help

??? tinm "There is No Magic!"

    The __ThoughtSpot__ team runs this command on a daily cadence. You can find it here in our [__GitHub Actions__](https://github.com/thoughtspot/cs_tools/actions/workflows/fetch-tml.yaml) and [__Workflow File__](https://github.com/thoughtspot/cs_tools/blob/6a8e43bba3140371109e79ef2de7309b7d2a21e5/.github/workflows/fetch-tml.yaml#L64-L72).

---

[gh-searchable-tml]: https://github.com/thoughtspot/cs_tools/tree/master/cs_tools/cli/tools/searchable/static
[tsa-mfs]: https://docs.thoughtspot.com/cloud/latest/data-modeling-settings
[syncer-base]: ../../syncer/what-is
[ts-rest-v2]: https://developers.thoughtspot.com/docs/rest-apiv2-reference
[ts-rest-orgs-search]: https://developers.thoughtspot.com/docs/restV2-playground?apiResourceId=http%2Fapi-endpoints%2Forgs%2Fsearch-orgs
[ts-rest-groups-search]: https://developers.thoughtspot.com/docs/restV2-playground?apiResourceId=http%2Fapi-endpoints%2Fgroups%2Fsearch-groups
[ts-rest-users-search]: https://developers.thoughtspot.com/docs/restV2-playground?apiResourceId=http%2Fapi-endpoints%2Fusers%2Fsearch-users
[ts-rest-tags-search]: https://developers.thoughtspot.com/docs/restV2-playground?apiResourceId=http%2Fapi-endpoints%2Ftags%2Fsearch-tags
[ts-rest-metadata-search]: https://developers.thoughtspot.com/docs/restV2-playground?apiResourceId=http%2Fapi-endpoints%2Fmetadata%2Fsearch-metadata
[ts-rest-metadata-security]: https://developers.thoughtspot.com/docs/restV2-playground?apiResourceId=http%2Fapi-endpoints%2Fsecurity%2Ffetch-permissions-on-metadata
[ts-rest-searchdata]: https://developers.thoughtspot.com/docs/restV2-playground?apiResourceId=http%2Fapi-endpoints%2Fdata%2Fsearch-data
[ts-rest-audit-logs]: https://developers.thoughtspot.com/docs/restV2-playground?apiResourceId=http%2Fapi-endpoints%2Flog%2Ffetch-logs
[ts-rest-metadata-tml-export]: https://developers.thoughtspot.com/docs/restV2-playground?apiResourceId=http%2Fapi-endpoints%2Fmetadata%2Fexport-metadata-tml
[ts-rest-metadata-tml-import]: https://developers.thoughtspot.com/docs/restV2-playground?apiResourceId=http%2Fapi-endpoints%2Fmetadata%2Fimport-metadata-tml