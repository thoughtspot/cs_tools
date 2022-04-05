# Extractor

It is often difficult to programmatically use the result set of a query that runs in the
ThoughtSpot UI search bar. To use the data that we retrieve from a query
programmatically, you can use this tool to just that.

When issuing a query through the ThoughtSpot UI, users make selections to disambiguate
a query. Your Search will need to be modified in order to extract data from the source.
See [Components of a search query][search-components].

??? todo "Coming soon, a recipe for this tool!"

    *Stay tuned, we'll have a full recipe for loading this data into various
    Embrace-supported cloud data warehouses*

    For now, you might try extracting from [TS: BI Server][tsbi]{ .external-link } with
    the following terms:

    ```
    [incident id] [timestamp.detailed] [url] [http response code] [browser type] [browser version] [client type]
    [client id] [answer book guid] [answer book name] [viz id] [user id] [user] [user action] [query text]
    [response size] [latency (us)] [impressions]
    ```

    This will allow you to bring together ThoughtSpot usage data with your own data sources.

## CLI preview

=== "extractor --help"
    ```console
    (.cs_tools) C:\work\thoughtspot\cs_tools>cs_tools tools extractor --help

     Usage: cs_tools tools extractor [--version, --help] <command>

      Extract data from a worksheet, view, or table in your platform.

    Options:
      --version   Show the version and exit.
      -h, --help  Show this message and exit.

    Commands:
      search  Search a dataset from the command line.
    ```

=== "extractor search"
    ```console
    (.cs_tools) C:\work\thoughtspot\cs_tools>cs_tools tools extractor search --help

    Usage: cs_tools tools extractor search [--option, ..., --help]

      Search a dataset from the command line.

      Columns must be surrounded by square brackets. Search-level formulas are not
      currently supported, but a formula defined as part of a data source is.

      There is a hard limit of 100K rows extracted for any given Search.

      Further reading:
        https://docs.thoughtspot.com/software/latest/search-data-api
        https://docs.thoughtspot.com/software/latest/search-data-api#components
        https://docs.thoughtspot.com/software/latest/search-data-api#_limitations_of_search_query_api

    Options:
      --query TEXT                    search terms to issue against the dataset  (required)
      --dataset TEXT                  name of the worksheet, view, or table to search
                                      against  (required)

      --export FILE.csv               full path to save data set to  (required)
      --data-type (worksheet|table|view)
                                      type of object to search  (default: worksheet)

      --helpfull                      Show the full help message and exit.
      -h, --help                      Show this message and exit.
    ```

---

## Changelog

!!! tldr ":octicons-tag-16: v1.0.0 &nbsp; &nbsp; :material-calendar-text: 2020-11-14"

    === ":hammer_and_wrench: &nbsp; Added"
        - Initial release [@boonhapus][contrib-boonhapus]{ target='secondary' .external-link }.

---

[tsbi]: https://cloud-docs.thoughtspot.com/admin/system-monitor/worksheets.html#description-of-system-worksheets-and-views
[search-components]: https://docs.thoughtspot.com/software/latest/search-data-api#components
[keep-a-changelog]: https://keepachangelog.com/en/1.0.0/
[semver]: https://semver.org/spec/v2.0.0.html
[contrib-boonhapus]: https://github.com/boonhapus
