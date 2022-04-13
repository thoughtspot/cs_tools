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
metadata object's modified/created time and the ThoughtSpot datetime function now()).
This could give you early warning when a user is missing a dataset that could provide
value to others in your platform.


## CLI preview

=== "searchable --help"
    ```console
    (.cs_tools) C:\work\thoughtspot\cs_tools>cs_tools tools searchable-content --help

    Usage: cs_tools tools searchable-content [--version, --help] <command>

      Make ThoughtSpot content searchable in your platform.

      USE AT YOUR OWN RISK! This tool uses private API calls which could change on any
      version update and break the tool.

      Metadata is created through normal ThoughtSpot activities. Tables, Worksheets,
      Answers, and Pinboards are all examples of metadata.

      Metadata Object
      - guid
      - name
      - description
      - author guid
      - author name
      - author display name
      - created
      - modified
      - object type

    Options:
      --version   Show the version and exit.
      -h, --help  Show this message and exit.

    Commands:
      gather   Gather and optionally, insert data into Falcon.
      spotapp  Exports the SpotApp associated with this tool.
    ```

=== "searchable gather"
    ```console
    (.cs_tools) C:\work\thoughtspot\cs_tools>cs_tools tools searchable-content gather --help

    Usage: cs_tools tools searchable-content gather [--option, ..., --help]

      Gather and optionally, insert data into Falcon.

      By default, data is automatically gathered and inserted into the platform. If
      --export argument is used, data will not be inserted and will instead be dumped
      to the location specified.

    Options:
      --export DIRECTORY              if specified, directory to save data to
      --metadata (system table|imported data|worksheet|view|pinboard|saved answer)
                                      type of object to find data for
      --helpfull                      Show the full help message and exit.
      -h, --help                      Show this message and exit.
    ```

=== "searchable bi-server"
    ```console
    (.cs_tools) C:\work\thoughtspot\cs_tools>cs_tools tools searchable-content spotapp --help

    Usage: cs_tools tools searchable-content spotapp [--option, ..., --help]

      Exports the SpotApp associated with this tool.

    Options:
      --export DIRECTORY  directory to save the spot app to
      --helpfull          Show the full help message and exit.
      -h, --help          Show this message and exit.
    ```

=== "searchable spotapp"
    ```console
    (.cs_tools) C:\work\thoughtspot\cs_tools>cs_tools tools searchable-content spotapp --help

    Usage: cs_tools tools searchable-content spotapp [--option, ..., --help]

      Exports the SpotApp associated with this tool.

    Options:
      --export DIRECTORY  directory to save the spot app to
      --helpfull          Show the full help message and exit.
      -h, --help          Show this message and exit.
    ```

---

## Changelog

!!! tldr ":octicons-tag-16: v1.3.0 &nbsp; &nbsp; :material-calendar-text: 2022-04-15"

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
