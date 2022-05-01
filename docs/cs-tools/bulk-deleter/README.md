# Bulk Deleter

Over the life of a ThoughtSpot cluster objects in the system grow. With changes in
employee roles and business problems you may find that tens of thousands of objects can
be left behind. This tool allows you to remove objects from the metadata enmasse. 

The tool separates deletes objects in batches that can be specified in the args to speed
up the delete process, but gives less visibility should an issue occur. A summary of
what has been removed is saved in the logs directory of cs-tools. 


=== "bulk-deleter --help"
    ```console
    (.cs_tools) C:\work\thoughtspot\cs_tools>cs_tools tools bulk-deleter --help
    Usage: cs_tools tools bulk-deleter [--version, --help] <command>

      Bulk delete metadata objects from your ThoughtSpot platform.

    Options:
      --version               Show the version and exit.
      -h, --help, --helpfull  Show this message and exit.

    Commands:
      from-tabular  Remove many objects from ThoughtSpot.
      single        Removes a specific object from ThoughtSpot.
    ```

=== "bulk-deleter from-tabular"
    ```console
    (.cs_tools) C:\work\thoughtspot\cs_tools>cs_tools tools bulk-deleter from-tabular --help

    Usage: cs_tools tools bulk-deleter from-tabular --config IDENTIFIER [--option, ..., --help]

      Remove many objects from ThoughtSpot.

      Objects to delete are limited to answers and liveboards, but can follow either naming convention of internal API
      type, or the name found in the user interface.

      If you are deleting from an external data source, your data must follow the
      tabular format below.

          +-----------------------+-------------+
          | object_type           | object_guid |
          +-----------------------+-------------+
          | saved answer          | guid1       |
          | pinboard              | guid2       |
          | liveboard             | guid3       |
          | ...                   | ...         |
          | QUESTION_ANSWER_BOOK  | guid4       |
          | PINBOARD_ANSWER_BOOK  | guid5       |
          | ...                   | ...         |
          +-----------------------+-------------+

    Options:
      --syncer protocol://DEFINITION.toml
                                      protocol and path for options to pass to the syncer
      --deletion TEXT                 if using --syncer, directive to find user deletion at
      --batchsize INTEGER             maximum amount of objects to delete simultaneously  (default: 1)
      --config IDENTIFIER             config file identifier  (required)
      -h, --help, --helpfull          Show this message and exit.
    ```

=== "bulk-deleter single"
    ```console
    (.cs_tools) C:\work\thoughtspot\cs_tools>cs_tools tools bulk-deleter single --help

    Usage: cs_tools tools bulk-deleter single --config IDENTIFIER [--option, ..., --help]

      Removes a specific object from ThoughtSpot.

    Options:
      --type (saved answer|pinboard|QUESTION_ANSWER_BOOK|PINBOARD_ANSWER_BOOK)
                                      type of the metadata to delete  (required)
      --guid TEXT                     guid to delete  (required)
      --config IDENTIFIER             config file identifier  (required)
      -h, --help, --helpfull          Show this message and exit.
    ```

---

## Changelog

!!! tldr ":octicons-tag-16: v1.1.0 &nbsp; &nbsp; :material-calendar-text: 2022-04-28"

    === ":wrench: &nbsp; Modified"
        - input/output using syncers! [@boonhapus][contrib-boonhapus]{ target='secondary' .external-link }.
        - updated to accept Liveboards

    === ":bug: &nbsp; Bugfix"
        - handle case where user submits an invalid object to be deleted (by type or guid)

??? info "Changes History"

    ??? tldr ":octicons-tag-16: v1.0.1 &nbsp; &nbsp; :material-calendar-text: 2021-11-09"
        === ":wrench: &nbsp; Modified"
            - now known as Bulk Deleter, `bulk-deleter`
            - `--save_path` is now `--export` [@boonhapus][contrib-boonhapus]{ target='secondary' .external-link }.

    ??? tldr ":octicons-tag-16: v1.0.0 &nbsp; &nbsp; :material-calendar-text: 2021-08-24"
        === ":hammer_and_wrench: &nbsp; Added"
            - Initial release from [@dpm][contrib-dpm]{ target='secondary' .external-link }.

---

[contrib-boonhapus]: https://github.com/boonhapus
[contrib-dpm]: https://github.com/DevinMcPherson-TS
