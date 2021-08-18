# CLS Sharing

**USE AT YOUR OWN RISK!**

**This tool uses private API calls which could change on any version update and break the tool.**

---

This solution allows the customer to manage column-level and table-level security models
within an easy to manipulate user interface.

Setting up Column Level Security (especially on larger tables) can be time-consuming
when done directly in the ThoughtSpot user interface. The web interface provided by this
tool will allow you to quickly understand the current security settings for a given
table across all columns, and as many groups as are in your platform. You may then set
the appropriate security settings for those group-table combinations.

## User Interface preview

<p align="center">
  <img src="./static/application.gif" width="1000" height="700" alt="user-interface">
</p>

## CLI preview

```console
(.cs_tools) C:\work\thoughtspot\cs_tools>cs_tools tools cls-sharing --help

Usage: cs_tools tools cls-sharing [OPTIONS] COMMAND [ARGS]...

  Scalably manage your table- and column-level security right in the browser.

  USE AT YOUR OWN RISK! This tool uses private API calls which could change on any version
  update and break the tool.

  Setting up Column Level Security (especially on larger tables) can be time-consuming when done directly in
  the ThoughtSpot user interface. The web interface provided by this tool will allow you to quickly understand
  the current security settings for a given table across all columns, and as many groups as are in your
  platform. You may then set the appropriate security settings for those group-table combinations.

Options:
  --version   Show the tool's version and exit.
  --helpfull  Show the full help message and exit.
  -h, --help  Show this message and exit.

Commands:
  run  Start the built-in webserver which runs the security management interface.
```
