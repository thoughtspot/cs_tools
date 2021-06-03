# CS Tools

ThoughtSpot CS Tools are a collection of different tools that assist implementation and
administration, and may contain API calls that we normally wouldn't share with
customers.

```console
(.cs_tools) C:\work\thoughtspot\cs_tools>cs_tools tools

Usage: cs_tools tools <tool-name> COMMAND [ARGS]...

  Run an installed tool.

  Tools are a collection of different scripts to perform different function which aren't native to the ThoughtSpot or
  advanced functionality for clients who have a well-adopted platform.

Options:
  --helpfull  Show the full help message and exit.
  -h, --help  Show this message and exit.

Commands:
  rtql                Enable querying the ThoughtSpot TQL CLI from a remote machine.
  rtsload             Enable loading files to ThoughtSpot from a remote machine.
  share-objects       Share one or more tables from a database with a specified user group.
  transfer-ownership  Transfer ownership of all objects from one user to another.
```

The tools are written in Python and require a Python environment in which to run. In the
project root directory, you will find a [dist/][dist] subdirectory. There are two sets
of INSTALL and ACTIVATE scripts for Windows and \*nix based platforms. See
[that directory][dist] for more information on deploying CS Tools.

By convention, a tool which uses ANY private APIs will have their app directory prefixed
with an underscore and **not** show up in the default cs_tools helptext. All tools are
runnable even if they are not shown. There is an undocumented `--private` flag if you
need to see the helptext for a private tool. This flag is not needed to run the tool
itself.

[dist]: ../../dist/
