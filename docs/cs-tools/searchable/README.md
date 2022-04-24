<style>
  .tabbed-block ul ul ul { columns: 3; }
</style>

# Searchable Content

This solution allows the customer to extract data on common ThoughtSpot metadata, and
make that information searchable within the platform.

As your platform grows, it can oftentimes be useful to keep track of how much content
is created within the system. For example, tracking the amount of answers or pinboards
created over time can help you understand how your Users interact with ThoughtSpot.

Another use case might be to set up a pinboard gating conditions based on when or how
often a user uploads data (eg. a combination of metadata type of "imported data", the 
metadata object's modified/created time and the ThoughtSpot datetime function `now()`).
This could give you early warning when a user is missing a dataset that could provide
value to others in your platform.


## CLI preview

=== "searchable --help"
    ```console
    (.cs_tools) C:\work\thoughtspot\cs_tools>cs_tools tools searchable --help
    Usage: cs_tools tools searchable [--help] <command>

      Explore your ThoughtSpot metadata, in ThoughtSpot!

    Options:
      --version               Show the version and exit.
      -h, --help, --helpfull  Show this message and exit.

    Commands:
      bi-server  Extract usage statistics from your ThoughtSpot platform.
      gather     Extract metadata from your ThoughtSpot platform.
    ```

=== "searchable gather"
    ```console
    (.cs_tools) C:\work\thoughtspot\cs_tools>cs_tools tools searchable gather --help

    Usage: cs_tools tools searchable gather --config IDENTIFIER [--option, ..., --help] protocol://DEFINITION.toml

      Extract metadata from your ThoughtSpot platform.

      See the full data model extract at the link below:   https://thoughtspot.github.io/cs_tools/cs-tools/searchable

    Arguments:
      protocol://DEFINITION.toml  protocol and path for options to pass to the syncer  (required)

    Options:
      --include-columns       ...
      --config IDENTIFIER     config file identifier  (required)
      -h, --help, --helpfull  Show this message and exit.
    ```

=== "searchable bi-server"
    ```console
    (.cs_tools) C:\work\thoughtspot\cs_tools>cs_tools tools searchable bi-server --help

    Usage: cs_tools tools searchable bi-server --config IDENTIFIER [--option, ..., --help] protocol://DEFINITION.toml

      Extract usage statistics from your ThoughtSpot platform.

      Fields extracted from TS: BI Server
          - incident id           - timestamp detailed    - url
          - http response code    - browser type          - client type
          - client id             - answer book guid      - viz id
          - user id               - user action           - query text
          - response size         - latency (us)          - database latency (us)
          - impressions

    Arguments:
      protocol://DEFINITION.toml  protocol and path for options to pass to the syncer  (required)

    Options:
      --from-date YYYY-MM-DD  lower bound of rows to select from TS: BI Server
      --to-date YYYY-MM-DD    upper bound of rows to select from TS: BI Server
      --include-today         if set, pull partial day data
      --compact / --full      if compact, exclude NULL and INVALID user actions  (default: compact)
      --config IDENTIFIER     config file identifier  (required)
      -h, --help, --helpfull  Show this message and exit.
    ```

---

## Changelog

!!! tldr ":octicons-tag-16: v1.3.0 &nbsp; &nbsp; :material-calendar-text: 2022-04-28"

    === ":wrench: &nbsp; Modified"
        - now known as simply Searchable, `searchable`
            - includes metadata about..
                - Tables
                - Views
                - Worksheets
                - Answers
                - Liveboards
                - Dependencies
                - Users
                - Groups
                - Privileges
                - Tags
                - Access Control
                - TS: BI Server

??? info "Changes History"

    ??? tldr ":octicons-tag-16: v1.2.1 &nbsp; &nbsp; :material-calendar-text: 2021-11-09"
        === ":wrench: &nbsp; Modified"
            - now known as Searchable Content, `searchable-content`
            - `--save_path` is now `--export` [@boonhapus][contrib-boonhapus]{ target='secondary' .external-link }.
            - `tml` is now `spotapp` [@boonhapus][contrib-boonhapus]{ target='secondary' .external-link }.

    ??? tldr ":octicons-tag-16: v1.2.0 &nbsp; &nbsp; :material-calendar-text: 2021-09-11"
        === ":wrench: &nbsp; Modified"
            - `ALTER TABLE` to support column dependencies [@boonhapus][contrib-boonhapus]{ target='secondary' .external-link }.
            - support for large clusters with API call batching [@boonhapus][contrib-boonhapus]{ target='secondary' .external-link }.

    ??? tldr ":octicons-tag-16: v1.1.0 &nbsp; &nbsp; :material-calendar-text: 2021-05-25"
        === ":wrench: &nbsp; Modified"
            - Migrated to new app structure [@boonhapus][contrib-boonhapus]{ target='secondary' .external-link }.

    ??? tldr ":octicons-tag-16: v1.0.0 &nbsp; &nbsp; :material-calendar-text: 2020-08-18"
        === ":hammer_and_wrench: &nbsp; Added"
            - Initial re-release [@boonhapus][contrib-boonhapus]{ target='secondary' .external-link }.


[contrib-boonhapus]: https://github.com/boonhapus
