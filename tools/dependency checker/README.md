ThoughtSpot CS Tools are a collection of different tools that assist implementation and
administration, but contain API usage that we normally wouldn't share with customers.
The tools and Web APIs are all written in Python and require a Python environment in
which to run.  The remainder of this document will describe how to deploy and use the
tools.

# Dependency Checking Tool

...

## Setup

All CS tools are installed as part of the Github CS Tools library.

You can install using `pip install --upgrade git+https://github.com/thoughtspot/cs_tools`

See the general [documentation][1] on setting up your environment and installing using
`pip`.

## Running the pre-built tools

It's as simple as opening a command window, referencing the full path of the tool, and
following the on-screen configuration. The configuration for this tool is below.

Try it now and verify your environment is all set.

~~~
usage: list_dependents.py [-h] --filename FILENAME [--toml TOML] [--ts_url TS_URL] [--username USERNAME] [--password PASSWORD] [--disable_ssl]
                          [--log_level INFO]

optional arguments:
  -h, --help           show this help message and exit
  --filename FILENAME  location of the CSV file to output dependents
  --toml TOML          location of the tsconfig.toml configuration file
  --ts_url TS_URL      the url to thoughtspot, https://my.thoughtspot.com
  --username USERNAME  frontend user to authenticate to ThoughtSpot with
  --password PASSWORD  frontend password to authenticate to ThoughtSpot with
  --disable_ssl        whether or not to ignore SSL errors
  --disable_sso        whether or not to disable SAML integration
  --log_level INFO     verbosity of the logger (used for debugging)
~~~ 

[1]: https://github.com/thoughtspot/community-tools/tree/master/python_tools
