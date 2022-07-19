# Scriptability

!!! caution "USE AT YOUR OWN RISK!"

    *__This tool uses private API calls!__ These could change with any version update and
    break the provided functionality.*

## Overview

This tool allows user to simplify and automate the extract and import of ThoughtSpot TML from and to the same or different instances.

There are several use cases where extracting and importing TML is useful:

1. Extract TML for version control.
2. Extract TML for migration to a different ThoughtSpot instance.
3. Extract TML to modify and create copies, such as for different customers or in different languages.

!!! danger "__This tool creates and updates content.  Regularly shapshots are recommended__"

    When importing content, it is possisible to accidentally overwrite content or create 
    multipl copies of content when you didn't intend to, just by using the wrong parameters.
    You should make sure you have a snapshot or backup prior to making large changes.

??? important "Scriptability enforces content rules"

    <span class=fc-coral>You __must__ have at least the __`Can Manage Data`__ privilege
    in ThoughtSpot to use this tool.</span>

    When exporting the TML, you will need content permissions to the content to be exported.  
    When importing the TML it will be created as the authenticated user of the tool.

!!! info "Helpful Links"

    :gear: &nbsp; __[Scriptability documentation][https://docs.thoughtspot.com/cloud/latest/scriptability]{ .external-link }__

    :material-github: &nbsp; __[Found a problem? Submit an issue.][gh-issue]{ target='secondary' .external-link }__</a>

This version of cstools scriptability supports the following scenarios:

* Extract TML based on specific GUIDs (with and without related content)
* Extract TML based on a ThoughtSpot TAG (with and without related content)
* :bring: Import TML (update and create new) with complex dependency handling (updated)
* :sparkles: Support a mapping file of GUIDs with automatic updates for new content (new)
* :sparkles: Compare two TML files for differences (new)
* :sparkles: Generate an empty mapping file (new)
* :sparkles: Share and tag content when importing (new)

!!! warning "Limitations"

    The following are some limitations of the existing tool:
    * Connections and tables cannot be imported

The following additional features are planned for an upcoming release:

* Export content based on the owner
* Set the owner on import
* Export and import SQL views (this might already work, but hasn't been tested)
* Import connections and tables

## Detailed scenarios

### Exporting TML for backup or check into version control

Some customers want to back up the metadata as TML in the file system or a version control system (VCS), such as `git`.  This is done simply by using the `scriptability --export` and saving the files to a directory.  Then you can use the VCS to add the TML. 

=== Migrate content

    Migrating content consist of exporting, (optionally) modifying, and then importing content.  You will want to do the following for this scenario:

    1. Create the connection and tables if they don't exist.  This step is needed because the scriptability tool doesn't currently support connections and tables.
    2. Create a mapping file for tables if one doesn't exist.  Note that you can use `scriptability create-mapping` to create a new, empty mapping file.
    3. Export the TML to be migrated using `scriptability export`.
    4. (Optional) Modify the TML as appropriate.  
    5. Import the TML using `scriptability import --force-create`.  The `force-create` parameter will make sure the content is created as new and not updating existing content.

    NOTE: To migrate changes, simply leave out the `--force-create` parameter.  New content will automatically be created and existing content (based on the mapping file) will be updated.

=== Updating content

    Updating and reimporting is basically the same steps as migrating new content.  In this step you would:

    1. Extract the TML using `scriptability export`.
    2. Modify the TML.
    3. Import the TML using `scriptability import` without the `--force-create` flag.  

=== Making copies 

    One scenario that comes up is that a ThoughtSpot administrator is managing content for different customers or groups.  They have a set of common content, but want to make copies for each group.  This can be done similarly to the migration of content, though it's usually back to the same instance.

    1. Extract the TML using `scriptability export`.
    2. Modify the TML for the group, such as different column names.
    3. Import the TML using `scriptability import` without the `--force-create` flag.

    In this scenario a mapping file _may_ be needed if the content comes from different connections.  In that case you may also want separate mapping files for each group to make a copy for.

    NOTE: This technique can also be used to localize content.  The modification step is to localize the content.  

## GUID mapping file

You will usually need to have an explicit mapping from one GUID to another.  This is particularly true of tables if 
there are more than one with the same name in the system being imported to.  If you don't provide the GUID as an 
FQN in the TML file, you will get an error on import, because ThoughtSpot won't know which table is being referred to.

The default name for the GUID mapping file is `guid.mapping`, but you can use whatever name you like since it's specified as a parameter.  The GUID mapping file is only used for importing TML.  When creating content, the GUID 
mapping file is updated as content is created with new GUID mappings.  This allows it to be used later for updating content.

The GUID mapping file is a [TOML](https://toml.io/en/) file with different sections.  The example below shows a starting file with mappings for tables.  

~~~
name = "TML Import"
source = "TS 1"
destination = "TS 2"
description = "Mapping file for TML migration."
version = "1.1.0"

[mappings]
"7ba07f4c-8756-48ef-bef0-0acc74f361f4"="73bc24b6-d3ff-4dae-bf82-61ae80f03dab" 
"a51f5b23-53c5-4703-ac0c-3bf5af649811"="11767209-e54d-4a26-ae63-92d1ab024051"
"dace214a-b8d6-46fd-927f-d03c0e06e62f"="5d9bf47d-79b6-45e4-acff-f7d166d2dee0"
~~~

The top section are values that tell the reader what the mapping file is for.  Note that good naming of the file is also recommended.  The `[mappings]` section contains mappings _from_ the old GUID _to_ the new GUID.  These would be from the source to the destination.  

Note that the file is updated and rewritten as new content is created.  TOML allows comments, but reading and writing comments is not supported.  A future version will have the ability to add some type of content, such as table names for the mappings.

## CLI preview

=== "scriptability --help"
    ```console
    (.cs_tools) C:\work\thoughtspot\cs_tools>cs_tools tools scriptability --help
    Usage: cs_tools tools scriptability <command>
                                                [--version, --help]

    Tool for easily migrating TML between instance.

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
      --export-ids GUIDS              comma separated list of GUIDs to export
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
