# Introspect: Users, Groups

!!! caution "USE AT YOUR OWN RISK!"

    *__This tool uses private API calls!__ These could change with any version update and
    break the provided functionality.*

This solution allows the customer to extract User and Group data, and make that
information searchable within the platform.

A best practice in ThoughtSpot is to have users be part of a Content-based group. This
Group will usually have a display name that is associated with a Use Case, or is a
parent of many use cases (think: a Finance UC can have Worksheets for Invoices Paid on
Time, Historicals, and Budget Forecast).

The data produced from this tool can be matched to the two activity worksheets,
TS: BI Server and TS: Embrace Stats Worksheet to get a better understanding of the
activity at a group level - which may proxy activity to a Use Case.

Ideally, make a plan with your customer for this solution to run on a regular interval
so that the information provided is not stale.

## Relationship preview

![user-group-relationship](./relationship.png)

## CLI preview

=== "introspect-user-group --help"
    ```console
    (.cs_tools) C:\work\thoughtspot\cs_tools>cs_tools tools introspect-user-group

    Usage: cs_tools tools introspect-user-group [OPTIONS] COMMAND [ARGS]...

      Make Users and Groups searchable in your platform.

      USE AT YOUR OWN RISK! This tool uses private API calls which could change on any
      version update and break the tool.

      Return data on your users, groups, and each users' group membership.

      Users                       Groups
      - guid                      - guid
      - email                     - description
      - name                      - name
      - display name              - display name
      - created                   - created
      - modified                  - modified
      - sharing visibility        - sharing visibility
      - user type                 - group type

    Options:
      --version   Show the tool's version and exit.
      --helpfull  Show the full help message and exit.
      -h, --help  Show this message and exit.

    Commands:
      gather  Gather and optionally, insert data into Falcon.
      tml     Create TML files.
    ```

=== "introspect-user-group gather"
    ```console
    (.cs_tools) C:\work\thoughtspot\cs_tools>cs_tools tools introspect-user-group gather --help

    Usage: cs_tools tools introspect-user-group gather [OPTIONS]

      Gather and optionally, insert data into Falcon.

      By default, data is automatically gathered and inserted into the platform. If save_path argument is
      used, data will not be inserted and will instead be dumped to the location specified.

    Options:
      --save-path PATH  if specified, directory to save data to
      --helpfull        Show the full help message and exit.
      -h, --help        Show this message and exit.
    ```

=== "introspect-user-group tml"
    ```console
    (.cs_tools) C:\work\thoughtspot\cs_tools>cs_tools tools introspect-user-group tml --help

    Usage: cs_tools tools introspect-user-group tml [OPTIONS]

      Create TML files.

      Generates and saves multiple TML files.

      TABLE:
        - introspect_user
        - introspect_group
        - introspect_asso_user_group

    Options:
      --save-path PATH  filepath to save TML files to  (required)
      --helpfull        Show the full help message and exit.
      -h, --help        Show this message and exit.
    ```
