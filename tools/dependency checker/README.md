# Dependency Checking Tool

This tool reveals all the dependencies of a given type of metadata object within your
ThoughtSpot platform. The output format is a CSV and includes both the parent and the
child GUID. The output CSV can then be imported back into ThoughtSpot, allowing you to
search on dependencies!

## Setup

If you are setting this tool up on behalf of a client, please see [Best Practices: Client Install][bp-client-install]
If you are setting this tool up for yourself, please see [Getting Started][cstools-getting-started]

## Running

It's as simple as opening a command window, referencing the full path of the tool, and
following the on-screen configuration. The configuration for this tool is below.

Try it now and verify your environment is all set.

~~~
usage: list_dependents.py [-h] [--toml TOML] [--ts_url TS_URL] [--log_level INFO] [--username USERNAME] [--password PASSWORD] [--disable_ssl] [--disable_sso]
                          --filename FILENAME
                          [--object_type {QUESTION_ANSWER_BOOK,PINBOARD_ANSWER_BOOK,QUESTION_ANSWER_SHEET,PINBOARD_ANSWER_SHEET,LOGICAL_COLUMN,LOGICAL_TABLE,LOGICAL_RELATIONSHIP,TAG,DATA_SOURCE}]

Find all objects in your ThoughtSpot platform of a specified type, and return their dependents.

optional arguments:
  -h, --help            show this help message and exit
  --toml TOML           location of the tsconfig.toml configuration file
  --ts_url TS_URL       the url to thoughtspot, https://my.thoughtspot.com
  --log_level INFO      verbosity of the logger (used for debugging)
  --version             display the current version of this tool
  --username USERNAME   frontend user to authenticate to ThoughtSpot with
  --password PASSWORD   frontend password to authenticate to ThoughtSpot with
  --disable_ssl         whether or not to ignore SSL errors
  --disable_sso         whether or not to disable SAML login redirect
  --filename FILENAME   location of the CSV file to output dependents
  --object_type {QUESTION_ANSWER_BOOK,PINBOARD_ANSWER_BOOK,QUESTION_ANSWER_SHEET,PINBOARD_ANSWER_SHEET,LOGICAL_COLUMN,LOGICAL_TABLE,LOGICAL_RELATIONSHIP,TAG,DATA_SOURCE}
                        type of object to find dependents from
~~~ 

[bp-client-install]: https://github.com/thoughtspot/cs_tools/tools
[cstools-getting-started]: https://github.com/thoughtspot/cs_tools/README.md#getting-started
