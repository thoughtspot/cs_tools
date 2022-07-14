# Searchable Content

!!! caution "USE AT YOUR OWN RISK!"

    *__This tool uses private API calls!__ These could change with any version update and
    break the provided functionality.*

This tool allows user to simplify and automate the extract and import of ThoughtSpot TML from and to the same or different instances.

There are several use cases where extracting and importing TML is useful:

1. Extract TML for version control.
2. Extract TML for migration to a different ThoughtSpot instance.
3. Extract TML to modify and create copies, such as for different customers or in different languages.

This version supports the following scenarios:

* Extract TML based on specific GUIDs (with and without related content)
* Extract TML based on a ThoughtSpot TAG (with and without related content)
* Import TML (update and create new) with complex dependency handling
* Support a mapping file of GUIDs with automatic updates for new content.
* Compare two TML files for differences.
* Generate an empty mapping file.
* Share and tag content when importing.

The following are some limitations of the existing software:

* Connections and tables cannot be imported

The following additional features are planned for the near future:

* Export content based on the owner
* Set the owner on import
* Export and import SQL views
* Create connections and tables

## CLI preview

=== "scriptability --help"
    ```console
    (.cs_tools) C:\work\thoughtspot\cs_tools>cs_tools tools scriptability --help
    Usage: cs_tools tools scriptability <command>
                                                [--version, --help]

    Tool for easily migrating TML between clusters.

    USE AT YOUR OWN RISK! This tool uses private API calls which
    could change on any version update and break the tool.

    ThoughtSpot provides the ability to extract object metadata (tables,
    worksheets, liveboards, etc.)  in ThoughtSpot Modeling Language (TML)
    format, which is a text format based on YAML.   These files can then be
    modified and imported into another (or the same) instance to either 
    create or modify objects.

    cs_tools tools scriptability --help

    Options:
      --version           Show the version and exit.
      --help, --helpfull  Show this message and exit.

    Commands:
      compare         Compares two TML files for differences.
      create-mapping  Create a new, empty mapping file.
      export          Exports TML as YAML from ThoughtSpot.
      import          Import TML from a file or directory into ThoughtSpot.
    ```

=== "scriptability compare"
    ```console
    (.cs_tools) C:\work\thoughtspot\cs_tools>cs_tools tools scriptability export --help

    Usage: cs_tools tools scriptability compare FILE1 FILE2
                                                            [--help]

      Compares two TML files for differences.

    Arguments:
      FILE1  full path to the first TML file to compare.  
      FILE2  full path to the second TML file to compare.  

    Options:
      --help, --helpfull  Show this message and exit.
    ```

=== "scriptability create-mapping"
    ```console
    (.cs_tools) C:\work\thoughtspot\cs_tools>cs_tools tools scriptability create-mapping --help

    Usage: cs_tools tools scriptability create-mapping 
               FILE [--help]
    
      Create a new, empty mapping file.
    
    Arguments:
      FILE  Path to the new mapping file to be created.  Existing files will not be overwritten.  
    
    Options:
      --help, --helpfull  Show this message and exit.
    ```

=== "scriptability export"
    ```console 
    (.cs_tools) C:\work\thoughtspot\cs_tools>cs_tools tools scriptability export --help

    Usage: cs_tools tools scriptability export DIR
                                                           [--tags, ...,
                                                           --help] --config
                                                           NAME
    
      Exports TML as YAML from ThoughtSpot.
    
    Arguments:
      DIR  full path (directory) to save data set to  
    
    Options:
      --tags TAGS                     comma separated list of tags to export
      --export-ids GUIDS              comma separated list of guids to export
      --export-associated / --no-export-associated
                                      if specified, also export related content
                                      [default: no-export-associated]
      --set-fqns / --no-set-fqns      if set, then the content in the TML will
                                      have FQNs (GUIDs) added.  \[default:
                                      no-set-fqns]
      --config NAME                   config file identifier  
      --help, --helpfull              Show this message and exit.
    ```

=== "scriptability import"
    ```console 
    (.cs_tools) C:\work\thoughtspot\cs_tools>cs_tools tools scriptability import --help

    Usage: cs_tools tools scriptability import FILE_OR_DIR
                                                           [--import-policy,
                                                           ..., --help]
                                                           --config NAME
    
      Import TML from a file or directory into ThoughtSpot.
    
    Arguments:
      FILE_OR_DIR  full path to the TML file or directory to import.  
    
    Options:
      --import-policy [PARTIAL|ALL_OR_NONE|VALIDATE_ONLY]
                                      The import policy type  \[default:
                                      VALIDATE_ONLY]
      --force-create / --no-force-create
                                      If true, will force a new object to be
                                      created.  \[default: no-force-
                                      create]
      --guid-file FILE_OR_DIR         Existing or new mapping file to map GUIDs
                                      from source instance to target instance.
      --tags TAGS                     One or more tags to add to the imported
                                      content.
      --share-with GROUPS             One or more groups to share the uploaded
                                      content with.
      --tml-logs DIR                  full path to the directory to log sent TML.
                                      TML can change during load.
      --config NAME                   config file identifier  
      --help, --helpfull              Show this message and exit.
    ```

---

## Changelog

!!! tldr ":octicons-tag-16: v1.0.0 &nbsp; &nbsp; :material-calendar-text: 2022-04-15"
    === ":hammer_and_wrench: &nbsp; Added"
    - Initial release [@billdback-ts][contrib-billdback-ts]{ target='secondary' .external-link }.

!!! tldr ":octicons-tag-16: v1.0.0 &nbsp; &nbsp; :material-calendar-text: 2022-04-15 "[@billdback-ts][contrib-billdback-ts]{ target='secondary' .external-link }.
=== ":hammer_and_wrench: &nbsp; Added"
Added the following capabilities:
* Create an empty mapping file.
* Compare two TML files.
* Create content with automatic dependency handling.
* Update content with automatic dependency handling.  
* Allow new and updated content to be shared with groups during import.
* Allow tags to be applied to new and updated content during import.

---

[keep-a-changelog]: https://keepachangelog.com/en/1.0.0/
[semver]: https://semver.org/spec/v2.0.0.html
[contrib-billdback-ts]: https://github.com/billdback-ts
