# Searchable Content

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

=== "searchable-content --help"
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

=== "searchable-content gather"
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

=== "searchable-content spotapp"
    ```console
    (.cs_tools) C:\work\thoughtspot\cs_tools>cs_tools tools searchable-content spotapp --help

    Usage: cs_tools tools searchable-content spotapp [--option, ..., --help]

      Exports the SpotApp associated with this tool.

    Options:
      --export DIRECTORY  directory to save the spot app to
      --helpfull          Show the full help message and exit.
      -h, --help          Show this message and exit.
    ```
