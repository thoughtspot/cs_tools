# Archiver

Archiver allows the ThoughtSpot admin to survey and identify all the content that users
create. This content can build up over time and cause maintenance and upgrades to run
more slowly. Additionally, your ThoughtSpot platform has some minor overhead when
holding references to all of these objects as well.

!!! danger "With great power, comes great responsibility!"

    Archiver is a tool that can perform mass modification and deletion of content in
    your platform! If not used appropriately, you could remove worthwhile answers and
    liveboards. __Your users trust you__, use this tool carefully.


## CLI preview

=== "archiver --help"
    ```console
    (.cs_tools) C:\work\thoughtspot\cs_tools>cstools tools archiver --help
    Usage: cstools tools archiver [--version, --help] <command>

      Manage stale answers and liveboards within your platform.

      As your platform grows, user-generated content will naturally grow. Sometimes, users will create content for temporary exploratory
      purposes and then abandon it for newer pursuits. Archiver enables you to identify, tag, export, and remove that potentially
      abandoned content.

    Options:
      --version               Show the version and exit.
      -h, --help, --helpfull  Show this message and exit.

    Commands:
      identify  Identify objects which objects can be archived.
      remove    Remove objects from the ThoughtSpot platform.
      revert    Remove objects from the temporary archive.
    ```

=== "archiver identify"
    !!! info "Selection criteria"

        The `identify` command will skip content owned by "System User" (system) and
        "Administrator" (tsamin)

    ```console
    (.cs_tools) C:\work\thoughtspot\cs_tools>cstools tools archiver identify --help

    Usage: cstools tools archiver identify --config IDENTIFIER [--option, ..., --help]

      Identify objects which objects can be archived.

      Identification criteria will skip content owned by "System User" (system) and "Administrator" (tsadmin)

      ThoughtSpot stores usage activity (default: 6 months of interactions) by user in the platform. If a user views, edits, or creates
      an Answer or Liveboard, ThoughtSpot knows about it. This can be used as a proxy to understanding what content is actively being
      used.

    Options:
      --tag TEXT                      tag name to use for labeling objects to archive (case sensitive)  (default: TO BE
                                      ARCHIVED)
      --content (answer|liveboard|all)
                                      type of content to archive  (default: all)
      --recent-activity INTEGER       days to IGNORE for content viewed or access (default: all history)
      --recent-modified INTEGER       days to IGNORE for content created or modified  (default: 100)
      --ignore-tag TEXT               tagged content to ignore (case sensitive), can be specified multiple times
      --dry-run                       test your selection criteria, doesn't apply tags
      --no-prompt                     disable the confirmation prompt
      --report protocol://DEFINITION.toml
                                      generates a list of content to be archived, utilizes protocol syntax
      --config IDENTIFIER             config file identifier  (required)
      -h, --help, --helpfull          Show this message and exit.
    ```

=== "archiver revert"
    ```console
    (.cs_tools) C:\work\thoughtspot\cs_tools>cstools tools archiver revert --help

    Usage: cstools tools archiver revert --config IDENTIFIER [--option, ..., --help]

      Remove objects from the temporary archive.

    Options:
      --tag TEXT                      tag name to revert on labeled content (case sensitive)  (default: TO BE
                                      ARCHIVED)
      --delete-tag                    remove the tag itself, after untagging identified content
      --dry-run                       test your selection criteria, doesn't revert tags
      --no-prompt                     disable the confirmation prompt
      --report protocol://DEFINITION.toml
                                      generates a list of content to be reverted, utilizes protocol syntax
      --config IDENTIFIER             config file identifier  (required)
      -h, --help, --helpfull          Show this message and exit.
    ```

=== "archiver remove"
    ```console
    (.cs_tools) C:\work\thoughtspot\cs_tools>cstools tools archiver remove --help

    Usage: cstools tools archiver remove --config IDENTIFIER [--option, ..., --help]

      Remove objects from the ThoughtSpot platform.

    Options:
      --tag TEXT                      tag name to use to remove objects (case sensitive)  (default: TO BE ARCHIVED)
      --export-tml FILE.zip           if set, path to export tagged objects as a zipfile
      --delete-tag                    remove the tag itself, after deleting identified content
      --export-only                   export all tagged content, but do not remove it from that platform
      --dry-run                       test your selection criteria, doesn't delete content
      --no-prompt                     disable the confirmation prompt
      --report protocol://DEFINITION.toml
                                      generates a list of content to be reverted, utilizes protocol syntax
      --config IDENTIFIER             config file identifier  (required)
      -h, --help, --helpfull          Show this message and exit.
    ```

---

## Changelog

!!! tldr ":octicons-tag-16: v1.1.0 &nbsp; &nbsp; :material-calendar-text: 2022-04-28"

    === ":hammer_and_wrench: &nbsp; Added"
        - `archiver.identify` can now ignore existing tags [@boonhapus][contrib-boonhapus]{ target='secondary' .external-link }.

    === ":wrench: &nbsp; Modified"
        - input/output using syncers! [@boonhapus][contrib-boonhapus]{ target='secondary' .external-link }.
        - more sensible default parameters for identification

??? info "Changes History"

    ??? tldr ":octicons-tag-16: v1.0.0 &nbsp; &nbsp; :material-calendar-text: 2021-05-24"
        === ":hammer_and_wrench: &nbsp; Added"
            - Initial release [@boonhapus][contrib-boonhapus]{ target='secondary' .external-link }.

[contrib-boonhapus]: https://github.com/boonhapus
