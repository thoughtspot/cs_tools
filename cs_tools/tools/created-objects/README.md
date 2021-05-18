# Created Objects

This tool will return details about a given type of metadata object within your
ThoughtSpot platform. The output format is a CSV can be imported back into the
platform, allowing you to search on all your metadata objects!

## Setup

If you are setting this tool up on behalf of a client, please see [Best Practices: Client Install][bp-client-install]

If you are setting this tool up for yourself, please see [Getting Started][cstools-getting-started]

## Running

It's as simple as opening a command window, running the command in the usage, and
following the on-screen configuration. The configuration for this tool is below.

Try it now and verify your environment is all set.

~~~
Usage: cs_tools tools created-objects [OPTIONS] COMMAND [ARGS]...

  Get details about a given type of metadata object.

  Metadata objects are concepts in ThoughtSpot that store data. Things like worksheet, answers,
  pinboards.

Options:
  -h, --help  Show this message and exit.

Commands:
  gather-data  Gather and optionally, insert data into Falcon.
~~~ 

[bp-client-install]: ../../best-practices/client-install.md
[cstools-getting-started]: ../../README.md#getting-started
