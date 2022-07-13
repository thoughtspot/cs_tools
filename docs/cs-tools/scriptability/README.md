# Searchable Content

!!! caution "USE AT YOUR OWN RISK!"

    *__This tool uses private API calls!__ These could change with any version update and
    break the provided functionality.*

This tool allows user to simplify and automate the extract and import of ThoughtSpot TML from and to the same or different instances.

There are several use cases where extracting and importing TML is useful:

1. Extract TML for version control.
2. Extract TML for migration to a different ThoughtSpot instance.
3. Extract TML to modify and create copies, such as for different customers or in different languages.

Note that this is v1.0.0 of the software and should be considered a first, minimal release.  It supports the following:

* Extract TML based on specific GUIDs (with and without related content)
* Extract TML based on a ThoughtSpot TAG (with and without related content)
* Import TML (update and create new)

The following are some limitations of the existing software:

* Connections and tables cannot be imported
* Content that is migrated to a new cluster is created as new unless GUIDs are manually modified in the TML files

The following additional features are planned for the near future:

* Map GUIDs from the old instance to the new instance in order to update content
* Share content with users
* Add tags to the imported content

## CLI preview

=== "scriptability --help"
    ```console
    (.cs_tools) C:\work\thoughtspot\cs_tools>cs_tools tools scriptability --help
    Usage: cs_tools tools scriptability [--version, --help] <command>

      Tool for easily migrating TML between clusters.

      USE AT YOUR OWN RISK! This tool uses private API calls which could change on any version update and break the
      tool.

      ThoughtSpot provides the ability to extract object metadata (tables, worksheets, liveboards, etc.)  in ThoughtSpot Modeling
      Language (TML) format, which is a text format based on YAML.   These files can then be modified and imported into another (or the
      same) instance to either create  or modify objects.

        cs_tools tools scriptability --help

    Options:
      --version               Show the version and exit.
      -h, --help, --helpfull  Show this message and exit.

    Commands:
      export  Exports TML as YAML from ThoughtSpot.
      import  Import TML from a file or directory into ThoughtSpot.
    ```

=== "scriptability export"
    ```console 
    (.cs_tools) C:\work\thoughtspot\cs_tools>cs_tools tools scriptability export --help

    Usage: cs_tools tools scriptability export --config IDENTIFIER [--option, ..., --help] DIR

      Exports TML as YAML from ThoughtSpot.

    Arguments:
      DIR  full path (directory) to save data set to  (required)

    Options:
      --tags TAGS                     comma separated list of tags to export
      --export-ids GUIDS              comma separated list of guids to export
      --export-associated / --no-export-associated
                                      if specified, also export related content  (default: no-export-associated)
      --config IDENTIFIER             config file identifier  (required)
      -h, --help, --helpfull          Show this message and exit.
    ```

=== "scriptability import"
    ```console 
    (.cs_tools) C:\work\thoughtspot\cs_tools>cs_tools tools scriptability import --help

    Usage: cs_tools tools scriptability import --config IDENTIFIER [--option, ..., --help] FILE_OR_DIR

      Import TML from a file or directory into ThoughtSpot.

    Arguments:
      FILE_OR_DIR  full path to the TML file or directory to import.  (required)

    Options:
      --import-policy (PARTIAL|ALL_OR_NONE|VALIDATE_ONLY)
                                      The import policy type  (default: VALIDATE_ONLY)
      --force-create / --no-force-create
                                      If true, will force a new object to be created.  (default: no-force-create)
      --connection TEXT               GUID for the target connection if tables need to be mapped to a new connection.
      --config IDENTIFIER             config file identifier  (required)
      -h, --help, --helpfull          Show this message and exit.
    ```

---

## Changelog

!!! tldr ":octicons-tag-16: v1.0.0 &nbsp; &nbsp; :material-calendar-text: 2022-04-15"
    === ":hammer_and_wrench: &nbsp; Added"
    - Initial release [@billdback-ts][contrib-billdback-ts]{ target='secondary' .external-link }.

---

[keep-a-changelog]: https://keepachangelog.com/en/1.0.0/
[semver]: https://semver.org/spec/v2.0.0.html
[contrib-billdback-ts]: https://github.com/billdback-ts
