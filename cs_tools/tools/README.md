# CS Tools

ThoughtSpot CS Tools are a collection of different tools that assist implementation and
administration, and may contain API calls that we normally wouldn't share with
customers.

The tools and Web APIs are all written in Python and require a Python environment in
which to run. In the project root directory, you will find a [dist/][dist] subdirectory.
There are two sets of INSTALL and ACTIVATE scripts for Windows and \*nix based
platforms. See [that directory][dist] for more information on deploying CS Tools.

By convention, a tool which uses ANY private APIs will have their app directory prefixed
with an underscore and **not** show up in the default cs_tools helptext. All tools are
runnable even if they are not shown. There is an undocumented `--private` flag if you
need to see the helptext for a private tool. This flag is not needed to run the tool
itself.

[dist]: ../../dist/
