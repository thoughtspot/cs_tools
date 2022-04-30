---
icon: format-list-bulleted
---

# Sharding Recommender

!!! caution "USE AT YOUR OWN RISK!"

    *__This tool uses private API calls!__ These could change with any version update and
    break the provided functionality.*

This solution allows the customer to extract key data about their Falcon tables to help
guide on the optimal number of shards for each table. Ideally, the customer will
implement this solution to run on a regular basis, with a plan to review the liveboard
once every few months (depending on data volume growth).

__Currently, this solution does not consider co-sharding as part of the output.__

If your customer is not comfortable with sharding, please have them schedule an
Office Hours session and a CSA will be able to help guide them through the process.

## Liveboard preview

![liveboard](./liveboard.png)

## CLI preview

=== "sharding-recommender --help"
    ```console
    (.cs_tools) C:\work\thoughtspot\cs_tools>cstools tools sharding-recommender --help
    Usage: cstools tools sharding-recommender [--version, --help] <command>

      Gather data on your existing Falcon tables for sharding.

      USE AT YOUR OWN RISK! This tool uses private API calls which could change on any version update and break the
      tool.

      Once tables grow sufficiently large within a Falcon deployment, cluster performance and data loading can be enhanced through the
      use of sharding. The choice of what column to shards and how many shards to use can vary based on many factors. This tool helps
      expose that key information.

      Before sharding, it can be helpful to implement this solution and consult with your ThoughtSpot contact for guidance on the best
      shard key and number of shards to use.

      For further information on sharding, please refer to:
        https://docs.thoughtspot.com/latest/admin/loading/sharding.html

    Options:
      --version               Show the version and exit.
      -h, --help, --helpfull  Show this message and exit.

    Commands:
      gather   Extract Falcon table info from your ThoughtSpot platform.
      spotapp  Exports the SpotApp associated with this tool.
    ```

=== "sharding-recommender gather"
    ```console
    (.cs_tools) C:\work\thoughtspot\cs_tools>cstools tools sharding-recommender gather --help

    Usage: cstools tools sharding-recommender gather --config IDENTIFIER [--option, ..., --help] protocol://DEFINITION.toml

      Extract Falcon table info from your ThoughtSpot platform.

    Arguments:
      protocol://DEFINITION.toml  protocol and path for options to pass to the syncer  (required)

    Options:
      --config IDENTIFIER     config file identifier  (required)
      -h, --help, --helpfull  Show this message and exit.
    ```

=== "sharding-recommender spotapp"
    ```console
    (.cs_tools) C:\work\thoughtspot\cs_tools>cstools tools sharding-recommender spotapp --help

    Usage: cstools tools sharding-recommender spotapp [--option, ..., --help] DIRECTORY

      Exports the SpotApp associated with this tool.

    Arguments:
      DIRECTORY  location on your machine to copy the SpotApp to  (required)

    Options:
      --nodes INTEGER         number of nodes serving your ThoughtSpot cluster  (required)
      --cpu-per-node INTEGER  number of CPUs serving each node  (default: 56)
      --threshold INTEGER     unsharded row threshold, once exceeded a table will be a candidate for sharding  (default:
                              55000000)
      --ideal-rows INTEGER    ideal rows per shard  (default: 20000000)
      --min-rows INTEGER      minumum rows per shard  (default: 15000000)
      --max-rows INTEGER      maximum rows per shard  (default: 20000000)
      -h, --help, --helpfull  Show this message and exit.
    ```

---

## Changelog

!!! tldr ":octicons-tag-16: v1.2.0 &nbsp; &nbsp; :material-calendar-text: 2022-04-28"

    === ":hammer_and_wrench: &nbsp; Added"
        - SpotApp parameters, customize the spot app to your specific ThoughtSpot instance

    === ":wrench: &nbsp; Modified"
        - input/output using syncers! [@boonhapus][contrib-boonhapus]{ target='secondary' .external-link }.

??? info "Changes History"

    ??? tldr ":octicons-tag-16: v1.1.2 &nbsp; &nbsp; :material-calendar-text: 2021-11-09"
        === ":wrench: &nbsp; Modified"
            - `--save_path` is now `--export` [@boonhapus][contrib-boonhapus]{ target='secondary' .external-link }.
            - `tml` is now `spotapp` [@boonhapus][contrib-boonhapus]{ target='secondary' .external-link }.

    ??? tldr ":octicons-tag-16: v1.1.1 &nbsp; &nbsp; :material-calendar-text: 2021-09-11"
        === ":wrench: &nbsp; Modified"
            - support for large clusters with API call batching [@boonhapus][contrib-boonhapus]{ target='secondary' .external-link }.

    ??? tldr ":octicons-tag-16: v1.0.1 &nbsp; &nbsp; :material-calendar-text: 2021-05-22"
        === ":wrench: &nbsp; Modified"
            - Migrated to new app structure [@boonhapus][contrib-boonhapus]{ target='secondary' .external-link }.

    ??? tldr ":octicons-tag-16: v1.0.0 &nbsp; &nbsp; :material-calendar-text: 2020-08-18"
        === ":hammer_and_wrench: &nbsp; Added"
            - Initial release [@boonhapus][contrib-boonhapus]{ target='secondary' .external-link }.

[contrib-boonhapus]: https://github.com/boonhapus
