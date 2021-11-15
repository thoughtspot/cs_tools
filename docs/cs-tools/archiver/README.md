# Archiver

Archiver allows an admin within the ThoughtSpot platform to survey and identify all the
content that the platform's users create. This content can build up over time and cause
maintenance and upgrades to run more slowly. Additionally, your ThoughtSpot platform has
some minor overhead when holding references to all of these objects as well.

With Archiver, the Admin can set up a content maintenance process that will tag all
content not opened or modified within the lifetime of recorded interactions within the 
system worksheet, TS: BI Server.

From here, the admin can notify all users of their visibly tagged and stale content, and
if the user chooses, they can remove the tag from their answer or pinboard to safeguard
it from removal.

Once the Admin has completed their deprecation cycle, Archiver will help you remove the
unused or unwanted content, optionally exporting it prior to removal.

!!! danger "With great power, comes great responsibility!"

    Archiver is a tool that can perform mass modification and deletion of content in
    your platform! If not used appropriately, you could remove worthwhile answers and
    pinboards. __Your users trust you__, use this tool carefully.

## CLI preview

=== "archiver --help"
    ```console
    (.cs_tools) C:\work\thoughtspot\cs_tools>cs_tools tools archiver --help

     Usage: cs_tools tools archiver [--version, --help] <command>

      Manage stale answers and pinboards within your platform.

      As your platform grows, users will create and use answers and pinboards.
      Sometimes, users will create content for temporary exploratory purpopses and then
      abandon it for newer pursuits. Archiver enables you to identify, tag, export, and
      remove that potentially abandoned content.

    Options:
      --version   Show the version and exit.
      -h, --help  Show this message and exit.

    Commands:
      identify  Identify objects which objects can be archived.
      remove    Remove objects from the ThoughtSpot platform.
      revert    Remove objects from the temporary archive.
    ```

=== "archiver identify"
    ```console
    (.cs_tools) C:\work\thoughtspot\cs_tools>cs_tools tools archiver identify --help

    Usage: cs_tools tools archiver identify [--option, ..., --help]

      Identify objects which objects can be archived.

      ThoughtSpot stores usage activity (by default, 6 months of interactions) by user
      in the platform. If a user views, edits, or creates an Answer or Pinboard,
      ThoughtSpot knows about it. This can be used as a proxy to understanding what
      content is actively being used.

    Options:
      --tag TEXT                      tag name to use for labeling objects to archive
                                      (default: TO BE ARCHIVED)
      
      --content (answer|pinboard|all)
                                      type of content to archive  (default: all)
      
      --usage-months INTEGER          months to consider for user activity
                                      (default: all user history)
      
      --ignore-recent INTEGER         window of days to ignore for newly created or
                                      modified content  (default: 30)

      --dry-run                       test selection criteria, do not apply tags and
                                      instead output information to console on content
                                      to be archived

      --no-prompt                     disable the confirmation prompt
      --report FILE.csv               generates a list of content to be archived
      --helpfull                      Show the full help message and exit.
      -h, --help                      Show this message and exit.
    ```

=== "archiver revert"
    ```console
    (.cs_tools) C:\work\thoughtspot\cs_tools>cs_tools tools archiver revert --help

    Usage: cs_tools tools archiver revert [--option, ..., --help]

      Remove objects from the temporary archive.

    Options:
      --tag TEXT         tag name to remove on labeled objects  (default: TO BE ARCHIVED)
      --delete-tag       remove the tag itself, after untagging identified objects
      --dry-run          test selection criteria, do not remove tags and instead output
                         information on content to be unarchived

      --no-prompt        disable the confirmation prompt
      --report FILE.csv  generates a list of content to be untagged
      --helpfull         Show the full help message and exit.
      -h, --help         Show this message and exit.
    ```

=== "archiver remove"
    ```console
    (.cs_tools) C:\work\thoughtspot\cs_tools>cs_tools tools archiver remove --help

    Usage: cs_tools tools archiver remove [--option, ..., --help]

      Remove objects from the ThoughtSpot platform.

    Options:
      --tag TEXT             tag name to remove on labeled objects
                             (default: TO BE ARCHIVED)

      --export-tml FILE.zip  if set, path to export tagged objects as a zipfile
      --delete-tag           remove the tag after deleting identified objects
      --export-only          export all tagged content, but do not remove it from that
                             platform

      --dry-run              test selection criteria, does not export/delete content and
                             instead output information to console on content to be
                             unarchived

      --no-prompt            disable the confirmation prompt
      --report FILE.csv      generates a list of content to be removed
      --helpfull             Show the full help message and exit.
      -h, --help             Show this message and exit.
    ```
