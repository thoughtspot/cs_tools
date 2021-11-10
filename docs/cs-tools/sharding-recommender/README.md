# Sharding Recommender

!!! caution "USE AT YOUR OWN RISK!"

    *__This tool uses private API calls!__ These could change with any version update and
    break the provided functionality.*

This solution allows the customer to extract key data about their Falcon tables to help
guide on the optimal number of shards for each table. Ideally, the customer will
implement this solution to run on a regular basis, with a plan to review the pinboard
once every few months (depending on data volume growth).

__Currently, this solution does not consider co-sharding as part of the output.__

If your customer is not comfortable with sharding, please have them schedule an
Office Hours session and a CSA will be able to help guide them through the process.

## Pinboard preview

![pinboard](./pinboard.png)

## CLI preview

=== "sharding-recommender --help"
    ```console
    (.cs_tools) C:\work\thoughtspot\cs_tools>cs_tools tools sharding-recommender

    Usage: cs_tools tools sharding-recommender [OPTIONS] COMMAND [ARGS]...

      Gather data on your existing Falcon tables for sharding.

      USE AT YOUR OWN RISK! This tool uses private API calls which could change on any
      version update and break the tool.

      Once tables grow sufficiently large within a Falcon deployment, cluster performance and data
      loading can be enhanced through the use of sharding. The choice of what column to shards and how
      many shards to use can vary based on many factors. This tool helps expose that key information.

      Before sharding, it can be helpful to implement this solution and consult with your ThoughtSpot
      contact for guidance on the best shard key and number of shards to use.

      For further information on sharding, please refer to:
        https://docs.thoughtspot.com/latest/admin/loading/sharding.html

    Options:
      --version   Show the tool's version and exit.
      --helpfull  Show the full help message and exit.
      -h, --help  Show this message and exit.

    Commands:
      gather   Gather and optionally, insert data into Falcon.
      spotapp  Exports the SpotApp associated with this tool.
    ```

=== "sharding-recommender gather"
    ```console
    (.cs_tools) C:\work\thoughtspot\cs_tools>cs_tools tools sharding-recommender gather --help

    Usage: cs_tools tools sharding-recommender gather [OPTIONS]

      Gather and optionally, insert data into Falcon.

      By default, data is automatically gathered and inserted into the platform. If save_path argument is
      used, data will not be inserted and will instead be dumped to the location specified.

    Options:
      --export DIRECTORY  directory to save the spot app to
      --helpfull          Show the full help message and exit.
      -h, --help          Show this message and exit.
    ```

=== "sharding-recommender spotapp"
    ```console
    (.cs_tools) C:\work\thoughtspot\cs_tools>cs_tools tools sharding-recommender spotapp --help

    Usage: cs_tools tools sharding-recommender spotapp [OPTIONS]

      Exports the SpotApp associated with this tool.

    Options:
      --export DIRECTORY  directory to save the spot app to
      --helpfull          Show the full help message and exit.
      -h, --help          Show this message and exit.
    ```
