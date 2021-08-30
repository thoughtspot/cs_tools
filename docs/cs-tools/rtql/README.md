# Remote TQL

This solution allows the customer to interact with the TQL utility from a remote
machine. There are three command for remote TQL:

 - Interactive, get the full TQL experience on your local machine
 - Command, execute a single TQL command
 - File, execute a set of commands

A benefit of using remote TQL is that it encourages and enforces security. If you are
running TQL within the software command line, you are most likely signed in under the
`admin` account. Remote TQL enforces privileges: the logged in user **must** have at
least the "Can Manage Data" privilege in ThoughtSpot.

## Interactive TQL preview

<img src="interactive_rtql.png" width="1000" alt="interactive-rtql">

## CLI preview

```console
(.cs_tools) C:\work\thoughtspot\cs_tools>cs_tools tools rtql --help
Usage: cs_tools tools rtql [OPTIONS] COMMAND [ARGS]...

  Enable querying the ThoughtSpot TQL CLI from a remote machine.

  TQL is the ThoughtSpot language for entering SQL commands. You can use TQL to view and modify schemas and data in
  tables.

  For further information on TQL, please refer to:
    https://docs.thoughtspot.com/latest/reference/sql-cli-commands.html
    https://docs.thoughtspot.com/latest/reference/tql-service-api-ref.html

Options:
  --version   Show the tool's version and exit.
  --helpfull  Show the full help message and exit.
  -h, --help  Show this message and exit.

Commands:
  command      Run a single TQL command on a remote server.
  file         Run multiple commands within TQL on a remote server.
  interactive  Run an interactive TQL session as if you were on the cluster.
```
