# Extractor

It is often difficult to programmatically use the result set of a query that runs in the
ThoughtSpot UI search bar. To use the data that we retrieve from a query
programmatically, you can use this tool to just that.

When issuing a query through the ThoughtSpot UI, users make selections to disambiguate
a query. Your Search will need to be modified in order to extract data from the source.
See [Components of a search query][search-components].


## CLI preview

=== "extractor --help"
    ```console
    (.cs_tools) C:\work\thoughtspot\cs_tools>cs_tools tools extractor --help
    Usage: cs_tools tools extractor [--version, --help] <command>

      Extract data from a worksheet, view, or table in your platform.

    Options:
      --version               Show the version and exit.
      -h, --help, --helpfull  Show this message and exit.

    Commands:
      search  Search a dataset from the command line.
    ```

=== "extractor search"
    ```console
    (.cs_tools) C:\work\thoughtspot\cs_tools>cs_tools tools extractor search --help

    Usage: cs_tools tools extractor search --config IDENTIFIER [--option, ..., --help]

      Search a dataset from the command line.

      Columns must be surrounded by square brackets. Search-level formulas are not currently supported, but a formula defined as part of
      a data source is.

    Options:
      --query TEXT                    search terms to issue against the dataset  (required)
      --dataset TEXT                  name of the worksheet, view, or table to search against  (required)
      --syncer protocol://DEFINITION.toml
                                      protocol and path for options to pass to the syncer  (required)
      --target TEXT                   syncer directive to load data to  (required)
      --data-type (worksheet|table|view)
                                      type of object to search  (default: RecordsetType.worksheet)
      --config IDENTIFIER             config file identifier  (required)
      -h, --help, --helpfull          Show this message and exit.
    ```

---

## Changelog

!!! tldr ":octicons-tag-16: v1.1.0 &nbsp; &nbsp; :material-calendar-text: 2022-04-28"

    === ":wrench: &nbsp; Modified"
        - input/output using syncers! [@boonhapus][contrib-boonhapus]{ target='secondary' .external-link }.

??? info "Changes History"

    ??? tldr ":octicons-tag-16: v1.0.0 &nbsp; &nbsp; :material-calendar-text: 2020-11-14"
        === ":hammer_and_wrench: &nbsp; Added"
            - Initial release [@boonhapus][contrib-boonhapus]{ target='secondary' .external-link }.

---

[tsbi]: https://cloud-docs.thoughtspot.com/admin/system-monitor/worksheets.html#description-of-system-worksheets-and-views
[search-components]: https://docs.thoughtspot.com/software/latest/search-data-api#components
[contrib-boonhapus]: https://github.com/boonhapus
