# Changes

## Restructured Project
1. top level directories
    - `/tests` - toplevel tests per project industry standard
    - `/thoughtspot` - this is our python layer to the swagger api, tql, etc
    - `/tools` - this is where all non-technical customer interfacing scripts live
2. models, models, models!
    - high modularity and extendibility and for ease of testing
    - private and public APIs represented well 
3. logging & tsconfig-template
    - simpler for debugging when a Cx runs into an issue
      1. e.g. "send us the logs & your config" will allow PS to be more agile in resolving issues with our own scripts
    - TOML vs YAML vs JSON
      1. Looking for a friendly human-readable format.
      2. YAML is great, but the syntax is very finnicky and there is little support for latest standard.
      3. TOML is highly minimal and aimed at even more human readability.
4. `pydantic` for validation
5. soon: `httpx` over `requests`
    - support for both HTTP/1.1 and HTTP/2.0
    - nearly a drop-in replacement for `requests`
    - future support for `async` is a matter of changing a few lines of code

# TODO

- unittests
- formalize base `tsconfig.toml`
- docstrings
- fix tools to work with new api structure
- impl `/periscope/*` ?

---

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
