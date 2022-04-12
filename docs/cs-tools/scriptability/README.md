# Searchable Content

!!! caution "USE AT YOUR OWN RISK!"

    *__This tool uses private API calls!__ These could change with any version update and
    break the provided functionality.*

This tool allows user to simplify and automate the extract and upload (import) of ThoughtSpot TML from and to the same or different instances.

There are several use cases where extracting and upload TML is useful:

1. Extract TML for version control.
2. Extract TML for migration to a different ThoughtSpot instance.
3. Extract TML to modify and create copies, such as for different customers or in different languages.

Note that this is v1.0.0 of the software and should be considered a first, minimal release.  It supports the following:

* Extract TML based on specific GUIDs (with and without related content)
* Extract TML based on a ThoughtSpot TAG (with and without related content)
* Import TML (update and create new)

The following are some limitations of the existing software:

* Connections and tables cannot be uploaded
* Content that is migrated to a new cluster is created as new unless GIUDs are manually modified in the TML files

The following additional features are planned for the near future:

* Map GUIDs from the old instance to the new instance in order to update content
* Share content with users
* Add tags to the uploaded content

## CLI preview

=== "scriptability export --help"
    ```console 
    $ cs_tools tools scriptability export --help

    Usage: cs_tools tools scriptability export [--option, ..., --help]

    Options:
      --tags TAGS                     list of tags to export for
      --export-ids GUIDS              list of guids to export
      --export-associated / --no-export-associated
                                      if specified, also export related content
                                      (default: no-export-
                                      associated)
      --path DIR                      full path (directory) to save data set to
      --helpfull                      Show the full help message and exit.
      -h, --help                      Show this message and exit.

    ```

=== "scriptability upload --help"
    ```console 
    $ cs_tools tools scriptability upload --help

    Usage: cs_tools tools scriptability upload [--option, ..., --help] FILE_OR_DIR

    Arguments:
      FILE_OR_DIR  full path to the TML file or directory to upload.
                   (required)

    Options:
      --import-policy (PARTIAL|ALL_OR_NONE|VALIDATE_ONLY)
                                      The import policy type
                                      (default: VALIDATE_ONLY)
      --force-create / --no-force-create
                                      If true, will force a new object to be
                                      created.  (default: no-
                                      force-create)
      --connection TEXT               GUID for the target connection if tables
                                      need to be mapped to a new connection.
      --helpfull                      Show the full help message and exit.
      -h, --help                      Show this message and exit.
    ```