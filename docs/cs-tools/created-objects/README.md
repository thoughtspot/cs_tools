# Created Objects

!!! caution "USE AT YOUR OWN RISK!"

    *__This tool uses private API calls!__ These could change with any version update and
    break the provided functionality.*

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

=== "created-objects --help"
    ```console
    (.cs_tools) C:\work\thoughtspot\cs_tools>cs_tools tools created-objects

    Usage: cs_tools tools created-objects [OPTIONS] COMMAND [ARGS]...

      Make ThoughtSpot content searchable in your platform.

      USE AT YOUR OWN RISK! This tool uses private API calls which could change on any
      version update and break the tool.

      Metadata is created through normal ThoughtSpot activities. Tables, Worksheets, Answers, and
      Pinboards are all examples of metadata.

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
      --version   Show the tool's version and exit.
      --helpfull  Show the full help message and exit.
      -h, --help  Show this message and exit.

    Commands:
      gather  Gather and optionally, insert data into Falcon.
      tml     Create TML files.
    ```

=== "created-objects gather"
    ```console
    (.cs_tools) C:\work\thoughtspot\cs_tools>cs_tools tools created-objects gather --help

    Usage: cs_tools tools created-objects gather [OPTIONS]

      Gather and optionally, insert data into Falcon.

      By default, data is automatically gathered and inserted into the platform. If save_path argument is
      used, data will not be inserted and will instead be dumped to the location specified.

    Options:
      --save-path PATH                if specified, directory to save data to
      --metadata (system table|imported data|worksheet|view|pinboard|saved answer)
                                      type of object to find data for
      --helpfull                      Show the full help message and exit.
      -h, --help                      Show this message and exit.
    ```

=== "created-objects tml"
    ```console
    (.cs_tools) C:\work\thoughtspot\cs_tools>cs_tools tools created-objects tml --help

    Usage: cs_tools tools created-objects tml [OPTIONS]

      Create TML files.

      Generates and saves multiple TML files.

      TABLE:
        - introspect_metadata_object

    Options:
      --save-path PATH  filepath to save TML files to  (required)
      --helpfull        Show the full help message and exit.
      -h, --help        Show this message and exit.
    ```
