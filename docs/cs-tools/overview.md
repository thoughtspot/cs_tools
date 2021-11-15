# Available Tools

CS Tools is a community maintained and supported project, written by the ThoughtSpot Professional Services & Customer
Success organizations. It is meant to augment built-in platform tools, help with administration of and enhance
adoption within your ThoughtSpot environment.

!!! danger "__All tools are provided as-is__"

    While every effort has been made to test and certify use of these tools in the various
    supported ThoughtSpot deployments, each environment is different. You should ALWAYS take
    a snapshot before you make any significant changes to your environment!

### Advanced Tools

Tools which are marked with a :see_no_evil: in the sidebar utilize unpublished, or
internal, API calls in your ThoughtSpot platform and thus ^^__could change with any
version or release__^^{ .fc-coral }. You should not rely on them for production-critical
workflows.

!!! info "Helpful Links"

    :smile: &nbsp; __[Installation Guide][docs-install]{ .internal-link }__

    :gear: &nbsp; __[Setup a configuration file][docs-howto-config]{ .internal-link }__

    :material-github: &nbsp; __[Found a problem? Submit an issue.][gh-issue]{ target='secondary' .external-link }__</a>

```console
(.cs_tools) C:\work\thoughtspot\cs_tools>cs_tools tools

 Usage: cs_tools tools [--help] <tool>

  Run an installed tool.

  Tools are a collection of different scripts to perform different functions which aren't native to the ThoughtSpot or advanced
  functionality for clients who have a well-adopted platform.

Options:
  -h, --help  Show this message and exit.

Tools:
  archiver            Manage stale answers and pinboards within your platform.
  extractor           Extract data from a worksheet, view, or table in your platform.
  rtql                Enable querying the ThoughtSpot TQL CLI from a remote machine.
  rtsload             Enable loading files to ThoughtSpot from a remote machine.
  security-sharing    Scalably manage your table- and column-level security right in the browser.
  transfer-ownership  Transfer ownership of all objects from one user to another.
```

[docs-install]: ../../how-to/install-upgrade-cs-tools
[docs-howto-config]: ../../how-to/configuration-file
[gh-issue]: https://github.com/thoughtspot/cs_tools/issues/new
