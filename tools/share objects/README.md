# Dependency Checking Tool

This tool uses the ThoughtSpot APIs to share an object with a single group.  Currently only tables 
can be shared, but additional object types (worksheets, answers, pinboards) will be added in the future.

## Setup

If you are setting this tool up on behalf of a client, please see [Best Practices: Client Install][bp-client-install]

If you are setting this tool up for yourself, please see [Getting Started][cstools-getting-started]

## Running

It's as simple as opening a command window, referencing the full path of the tool, and
following the on-screen configuration. The configuration for this tool is below.

Try it now and verify your environment is all set.

~~~
usage: share_objects.py [-h] [--toml TOML] [--ts_url TS_URL]
                        [--log_level INFO] [--version] [--username USERNAME]
                        [--password PASSWORD] [--disable_ssl] [--disable_sso]
                        [--group GROUP] [--permission {view,edit,remove}]
                        [--database DATABASE] [--schema SCHEMA]
                        [--table TABLE]

Share objects with groups.

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
  --group GROUP         Group to share with.
  --permission {view,edit,remove}
                        Type of permission to assign.
  --database DATABASE   Database name of tables to share.
  --schema SCHEMA       Schema name of tables to share. Defaults to
                        'falcon_default_schema'
  --table TABLE         Name of table to share. If not provided, all tables in
                        the database will be shared.

Additional help can be found at https://github.com/thoughtspot/cs_tools
~~~ 

[bp-client-install]: ../../best-practices/client-install.md
[cstools-getting-started]: ../../README.md#getting-started
