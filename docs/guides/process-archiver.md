---
hide:
  - navigation
---

# Archiver

Clean up your stale and forgotten __Answers__{ .fc-green } and __Liveboards__{ .fc-purple } to improve the health of
your __ThoughtSpot__ platform.

Part of running an efficient ThoughtSpot cluster is ensuring you maintain a healthy balance of new and existing content.
As Administrators and Data Managers, we want to encourage users to find and interact with Answer and Liveboards which
meaningfully drive the business forward.

Once your ThoughtSpot adoption grows, it is a good practice to regularly `identify` stale user content and remove it
from the system. This helps your users continue to find relevant, timely, and useful content to interact with.

??? tinm "There is No Magic!"

    Remember, __CS Tools__ wraps the __ThoughtSpot__ [__REST APIs__][ts-rest-v2]. This tool uses the following endpoints.

    - [`/searchdata`][ts-rest-searchdata] *for fetching Object interaction activity*{ .fc-gray }
    - [`/metadata/search`][ts-rest-metadata-search] *for fetching Object modification activity*{ .fc-gray }
    - [`/tags/assign`][ts-rest-tags-assign] *for tagging content*{ .fc-gray }
    - [`/metadata/tml/export`][ts-rest-metadata-tml-export] *for exporting tagged content*{ .fc-gray }
    - [`/metadata/delete`][ts-rest-metadata-delete] *for removing tags and deleting tagged content*{ .fc-gray }

!!! tip ""

    === "--help"
        ??? abstract "Get the Command"
            ```shell
            cs_tools tools archiver --help
            ```
        ~cs~tools tools archiver --help
    === "identify"
        ??? abstract "Get the Command"
            ```shell
            cs_tools tools archiver identify --help
            ```
        ~cs~tools tools archiver identify --help
    === "untag"
        ??? abstract "Get the Command"
            ```shell
            cs_tools tools archiver untag --help
            ```
        ~cs~tools tools archiver untag --help
    === "remove"
        ??? abstract "Get the Command"
            ```shell
            cs_tools tools archiver remove --help
            ```
        ~cs~tools tools archiver remove --help

---

### Define a Process

!!! danger "Critical"

    This step is important!! The Archiver is a bulk operation tool which can delete many objects at once. It's important
    to be careful!

Run the `identify` command to identify stale content using the same value for both `--recent-activity` and
`--recent-modified` to define an "inactivity" threshold. Any visualization object which has not been opened, edited, or
saved during this time will be identified in your __ThoughtSpot__ cluster with the tag name you specify with `--tag`.

<sub class=fc-purple>
  <b>Use the</b> `--syncer` <b>parameter to export a [CSV][syncer-csv] of the tagged objects and their respective owners.</b>
</sub>

!!! tip ""
    ??? abstract "Get the Command"
        ```shell
        cs_tools tools archiver identify --help
        ```
    ~cs~tools tools archiver identify --help

---

### Communicate with Users

Let your Users know that their visualizations may be removed from the __ThoughtSpot__ platform.

This is a good opportunity to leverage your internal :material-slack: __Slack__ or :material-microsoft-teams:
__Microsoft Teams__ channels.

> __SAMPLE COMMUNICATION__{ .fc-green }
>
> *For the health and stability of the ThoughtSpot cluster, your Administration team is planning a reduction of
> unutilized visualizations. As of `YYYY/MM/DD`, we will be removing all Answers and Liveboards tagged with the
> `INACTIVE` tag.
>
> If you wish to keep your visualization or opt-out of the cleaning process, please remove the tag prior to
> `YYYY/MM/DD`.*
>

You should provide clear timelines to Users and aim for a 2 weeks notice before removing their visualizations.

---

### Clean Up the Cluster

Run the `remove` command to delete any content which still has the `INACTIVE` tag.

!!! danger "Critical"

    __Remember__{ .fc-red } this is a :bomb: __DESTRUCTIVE__{ .fc-red } activity!

__CS Tools__ provides you the ability to export all tagged objects prior to removal from __ThoughtSpot__ using the
`--directory PATH` and `--export-only` parameters. Using this alongside the `--syncer csv://directory=PATH` will provide
you a total guarantee that you can restore the deleted object if a user comes back and requests it.

!!! tip ""
    ??? abstract "Get the Command"
        ```shell
        cs_tools tools archiver remove --help
        ```
    ~cs~tools tools archiver remove --help


[syncer-csv]: ../../syncer/csv
[ts-rest-v2]: https://developers.thoughtspot.com/docs/rest-apiv2-reference
[ts-rest-searchdata]: https://developers.thoughtspot.com/docs/restV2-playground?apiResourceId=http%2Fapi-endpoints%2Fdata%2Fsearch-data
[ts-rest-metadata-search]: https://developers.thoughtspot.com/docs/restV2-playground?apiResourceId=http%2Fapi-endpoints%2Fmetadata%2Fsearch-metadata
[ts-rest-tags-assign]: https://developers.thoughtspot.com/docs/restV2-playground?apiResourceId=http%2Fapi-endpoints%2Ftags%2Fassign-tag
[ts-rest-metadata-tml-export]: https://developers.thoughtspot.com/docs/restV2-playground?apiResourceId=http%2Fapi-endpoints%2Fmetadata%2Fexport-metadata-tml
[ts-rest-metadata-delete]: https://developers.thoughtspot.com/docs/restV2-playground?apiResourceId=http%2Fapi-endpoints%2Fmetadata%2Fdelete-metadata
