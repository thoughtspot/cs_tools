# Created Objects

***This tool utilizes private API calls.***

This solution allows the customer to extract data on common ThoughtSpot metadta, and
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

```console
(.cs_tools) C:\work\thoughtspot\cs_tools>cs_tools tools created-objects --help
Usage: cs_tools tools created-objects [OPTIONS] COMMAND [ARGS]...

  Make ThoughtSpot content searchable in your platform.

  Metadata is created through normal ThoughtSpot activities. Tables, Worksheets, Answers, and Pinboards are all
  examples of metadata.

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
