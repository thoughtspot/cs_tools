# Archiver

...

## CLI preview

=== "archiver --help"
    ```console
    (.cs_tools) C:\work\thoughtspot\cs_tools>cs_tools tools archiver

    Usage: cstools tools archiver [OPTIONS] COMMAND [ARGS]...

      Manage stale answers and pinboards within your platform.

      As your platform grows, users will create and use answers and pinboards. Sometimes, users will
      create content for temporary exploratory purpopses and then abandon it for newer pursuits. Archiver
      enables you to identify, tag, export, and remove that potentially abandoned content.

    Options:
      --version   Show the tool's version and exit.
      --helpfull  Show the full help message and exit.
      -h, --help  Show this message and exit.

    Commands:
      identify  Identify objects which objects can be archived.
      remove    Remove objects from the ThoughtSpot platform.
      revert    Remove objects from the temporary archive.
    ```

=== "archiver identify"
    ```console
    (.cs_tools) C:\work\thoughtspot\cs_tools>cs_tools tools archiver identify --help

    Usage: cstools tools archiver identify [OPTIONS]

      Identify objects which objects can be archived.

      ThoughtSpot stores usage activity (by default, 6 months of interactions) by user in the platform.
      If a user views, edits, or creates an Answer or Pinboard, ThoughtSpot knows about it. This can be
      used as a proxy to understanding what content is actively being used.

    Options:
      --tag TEXT                      tag name to use for labeling objects to archive
                                      (default: TO BE ARCHIVED)

      --content (answer|pinboard|all)
                                      type of content to archive  (default: all)
      --usage-months INTEGER          months to consider for user activity (default: all user
                                      history)

      --dry-run                       test selection criteria, do not apply tags and instead output
                                      information to console on content to be archived

      --no-prompt                     disable the confirmation prompt
      --helpfull                      Show the full help message and exit.
      -h, --help                      Show this message and exit.
    ```

=== "archiver revert"
    ```console
    (.cs_tools) C:\work\thoughtspot\cs_tools>cs_tools tools archiver revert --help

    Usage: cstools tools archiver revert [OPTIONS]

      Remove objects from the temporary archive.

    Options:
      --tag TEXT    tag name to remove on labeled objects  (default: TO BE ARCHIVED)
      --delete-tag  remove the tag itself, after untagging identified objects
      --dry-run     test selection criteria, do not remove tags and instead output information on content
                    to be unarchived

      --no-prompt   disable the confirmation prompt
      --helpfull    Show the full help message and exit.
      -h, --help    Show this message and exit.
    ```

=== "archiver remove"
    ```console
    (.cs_tools) C:\work\thoughtspot\cs_tools>cs_tools tools archiver remove --help

    Usage: cstools tools archiver remove [OPTIONS]

      Remove objects from the ThoughtSpot platform.

    Options:
      --tag TEXT         tag name to remove on labeled objects  (default: TO BE
                         ARCHIVED)

      --export-tml PATH  if set, file path to export tagged objects, as zipfile
      --delete-tag       remove the tag after deleting identified objects
      --export-only      export all tagged content, but do not remove it from that platform
      --dry-run          test selection criteria, does not export/delete content and instead output
                         information to console on content to be unarchived

      --no-prompt        disable the confirmation prompt
      --helpfull         Show the full help message and exit.
      -h, --help         Show this message and exit.
    ```
