# Dependency Checker

!!! caution "USE AT YOUR OWN RISK!"

    *__This tool uses private API calls!__ These could change with any version update and
    break the provided functionality.*

This solution allows the customer to Search all metadata that could produce a dependent.
These metadata types include System Tables, Imported Data, Worksheets, and Views.

This solution can be highly useful when planning out a Falcon to Embrace migration, when
re-designing a data model for a Worksheet, or just for keeping tabs on what types of
content a User makes.

## Relationship preview

![user-group-relationship](./relationship.png)

## CLI preview

=== "dependency-checker --help"
    ```console
    (.cs_tools) C:\work\thoughtspot\cs_tools>cs_tools tools dependency-checker

    Usage: cs_tools tools dependency-checker [OPTIONS] COMMAND [ARGS]...

      Make Dependencies searchable in your platform.

      USE AT YOUR OWN RISK! This tool uses private API calls which could change on any
      version update and break the tool.

      Dependencies can be collected for various types of metadata. For example, many tables are used
      within a worksheet, while many worksheets will have answers and pinboards built on top of them.

      Metadata Object             Metadata Dependent
      - guid                      - guid
      - name                      - parent guid
      - description               - name
      - author guid               - description
      - author name               - author guid
      - author display name       - author name
      - created                   - author display name
      - modified                  - created
      - object type               - modified
      - context                   - object type

    Options:
      --version   Show the tool's version and exit.
      --helpfull  Show the full help message and exit.
      -h, --help  Show this message and exit.

    Commands:
      gather   Gather and optionally, insert data into Falcon.
      spotapp  Exports the SpotApp associated with this tool.
    ```

=== "dependency-checker gather"
    ```console
    (.cs_tools) C:\work\thoughtspot\cs_tools>cs_tools tools dependency-checker gather --help

Usage: cs_tools tools dependency-checker gather [OPTIONS]

      Gather and optionally, insert data into Falcon.

      By default, data is automatically gathered and inserted into the platform. If save_path argument is
      used, data will not be inserted and will instead be dumped to the location specified.

    Options:
      --export DIRECTORY              directory to save the spot app to
      --parent (system table|imported data|worksheet|view)
                                      type of object to find dependents for
      --include-columns               whether or not to find column dependents
      --helpfull                      Show the full help message and exit.
      -h, --help                      Show this message and exit.
    ```

=== "dependency-checker spotapp"
    ```console
    (.cs_tools) C:\work\thoughtspot\cs_tools>cs_tools tools dependency-checker spotapp --help

    Usage: cs_tools tools dependency-checker spotapp [OPTIONS]

      Exports the SpotApp associated with this tool.

    Options:
      --export DIRECTORY  directory to save the spot app to
      --helpfull          Show the full help message and exit.
      -h, --help          Show this message and exit.
    ```
