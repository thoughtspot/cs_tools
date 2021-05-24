# Introspect Users & Groups

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

<p align="center">
  <img src="./static/relationship.png" width="1000" height="700" alt="user-group-relationship">
</p>


## CLI preview

```console
(.cs_tools) C:\work\thoughtspot\cs_tools>cs_tools tools introspect-user-group --help
Usage: cs_tools tools introspect-user-group [OPTIONS] COMMAND [ARGS]...

  Make your Users and Groups searchable.

  Return data on your users, groups, and each users' group membership.

  Users                       Groups
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
