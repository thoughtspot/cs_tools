# Customer Success (Internal) Tools

Customer Success Tools SHOULD NOT to be shared outside ThoughtSpot or our partners since they use
internal APIs and databases that are not supported.  You have been warned!

ThoughtSpot CS Tools are a collection of different tools that assist implementation and administration, but contain
API usage that we normally wouldn't share with customers. The tools and Web APIs are all written in Python and 
require a Python environment in which to run.  The remainder of this document will describe how to deploy and use 
the tools.

## Packages and scripts

The tools can be split into two broad categories.  The first category contains the scripts that you can run to 
directly do things.  For example, the `list_dependencies` script will let you find all of the tables and their
dependencies in a cluster.

The second category are the ThoughtSpot Web API Python wrappers.  These are all contained in the cst package and 
categorized into modules based on functionality, such as API calls, data models, and reading and writing.

## Setup

CS Tools is installed with the same process as other TS Python tools.

You can install using `pip install --upgrade git+https://github.com/thoughtspot/cs_tools`

See the general [documentation](https://github.com/thoughtspot/community-tools/tree/master/python_tools) on setting 
up your environment and installing using `pip`.

## Running the pre-built tools

All of the pre-built tools are run using the general format: 

`python -m cstools.<tool-name>`

Note there is no `.py` at the end and you *must* use `python -m`.  So for example to run `list_dependencies` and see the 
options, you would enter `python -m cstools.list_dependencies --help`  Try it now and verify your environment is all set.

The user tools currently consist of four scripts:
1. `list_dependencies`, which gets all of the tables and dependencies and writes to stdout or Excel.

~~~
usage: cstools.list_dependencies [-h] [--tsurl TSURL] [--username USERNAME]
                                 [--password PASSWORD] [--disable_ssl]
                                 [--output_type OUTPUT_TYPE] [--filename FILENAME]
                                 [--ignore_ts]

optional arguments:
  -h, --help            show this help message and exit
  --tsurl TSURL         URL to ThoughtSpot, e.g. https://myserver
  --username USERNAME   Name of the user to log in as.
  --password PASSWORD   Password for login of the user to log in as.
  --disable_ssl         Will ignore SSL errors.
  --output_type OUTPUT_TYPE
                        Where to write results: stdout, xls, excel.
  --filename FILENAME   Name of the file for Excel files.
  --ignore_ts           Ignore files that start with 'TS:'.
 ~~~ 