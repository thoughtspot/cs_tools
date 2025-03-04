---
hide:
  - navigation
---

# Archiver

Clean up your stale and forgotten __Answers__{ .fc-green } and __Liveboards__{ .fc-purple } to improve the health of
your __ThoughtSpot__ platform.

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

## Define a Process

Part of running an efficient ThoughtSpot cluster is ensuring you maintain a healthy balance of new and existing content.
As Administrators and Data Managers, we want to encourage users to find and interact with Answer and Liveboards which
meaningfully drive the business forward.

Once your ThoughtSpot adoption grows, it is a good practice to regularly `identify` stale user content and remove it
from the system. This helps your users continue to find relevant, timely, and useful content to interact with.

!!! tip ""
    ??? abstract "Get the Command"
        ```shell
        cs_tools tools archiver identify --help
        ```

    ~cs~tools tools archiver identify --help

Run the `identify` command to identify stale content with the same value for both `--recent-activity` and
`--recent-modified` to define an "inactivity" threshold. Any user-object which has not been opened, edited, or saved
during this time will be identified in your __ThoughtSpot__ cluster with the tag name you specify with `--tag`.



[ts-rest-v2]: https://developers.thoughtspot.com/docs/rest-apiv2-reference
[ts-rest-searchdata]: https://developers.thoughtspot.com/docs/restV2-playground?apiResourceId=http%2Fapi-endpoints%2Fdata%2Fsearch-data
[ts-rest-metadata-search]: https://developers.thoughtspot.com/docs/restV2-playground?apiResourceId=http%2Fapi-endpoints%2Fmetadata%2Fsearch-metadata
[ts-rest-tags-assign]: https://developers.thoughtspot.com/docs/restV2-playground?apiResourceId=http%2Fapi-endpoints%2Ftags%2Fassign-tag
[ts-rest-metadata-tml-export]: https://developers.thoughtspot.com/docs/restV2-playground?apiResourceId=http%2Fapi-endpoints%2Fmetadata%2Fexport-metadata-tml
[ts-rest-metadata-delete]: https://developers.thoughtspot.com/docs/restV2-playground?apiResourceId=http%2Fapi-endpoints%2Fmetadata%2Fdelete-metadata
