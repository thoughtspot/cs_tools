# User Management

Bulk management of users within ThoughtSpot.........

## CLI preview

=== "user-management --help"
    ```console
    (.cs_tools) C:\work\thoughtspot\cs_tools>cs_tools tools user-management --help
    Usage: cs_tools tools user-management [--version, --help] <command>

      Managing Users and Groups in bulk.

    Options:
      --version               Show the version and exit.
      -h, --help, --helpfull  Show this message and exit.

    Commands:
      rename    Remap Users from one username to another.
      sync      Sync your Users and Groups from an external data source.
      transfer  Transfer ownership of objects from one User to another.
    ```

=== "user-management rename"
    ```console
    (.cs_tools) C:\work\thoughtspot\cs_tools>cs_tools tools user-management rename --help

    Usage: cs_tools tools user-management rename --config IDENTIFIER [--option, ..., --help]

      Remap Users from one username to another.

      If you are renaming from an external data source, your data must follow the tabular format below.

      +----------------+---------------------------+
      | from_username  |        to_username        |
      +----------------+---------------------------+
      | cs_tools       | cstools                   |
      | namey.namerson | namey@thoughtspot.com     |
      | fake.user      | fake.user@thoughtspot.com |
      +----------------+---------------------------+

    Options:
      --from TEXT                     current username
      --to TEXT                       new username
      --syncer protocol://DEFINITION.toml
                                      protocol and path for options to pass to the syncer
      --remapping TEXT                if using --syncer, directive to find user remapping at
      --config IDENTIFIER             config file identifier  (required)
      -h, --help, --helpfull          Show this message and exit.
    ```

=== "user-management sync"
    ```console
    (.cs_tools) C:\work\thoughtspot\cs_tools>cs_tools tools user-management sync --help

    Usage: cs_tools tools user-management sync --config IDENTIFIER [--option, ..., --help] protocol://DEFINITION.toml

      Sync your Users and Groups from an external data source.

      During this operation, Users and Groups..
      - present in ThoughtSpot, but not present in Syncer are deleted in ThoughtSpot
        - if using the --no-remove-deleted flag, users will not be deleted in this case
      - not present in ThoughtSpot, but present in Syncer are created in ThoughtSpot
      - present in ThoughtSpot, and in Syncer are updated by their attributes
        - this includes group membership

    Arguments:
      protocol://DEFINITION.toml  protocol and path for options to pass to the syncer  (required)

    Options:
      --users TEXT                    directive to find users to sync at  (default: ts_auth_sync_users)
      --groups TEXT                   directive to find groups to sync at  (default: ts_auth_sync_groups)
      --associations TEXT             directive to find associations to sync at  (default: ts_auth_sync_xref)
      --apply-changes                 whether or not to sync the security strategy into ThoughtSpot
      --new-user-password TEXT        password for new users added during the sync operation
      --dont-remove-deleted / --no-dont-remove-deleted
                                      whether to remove the deleted users and user groups
      --export                        whether or not to dump data to the syncer
      --config IDENTIFIER             config file identifier  (required)
      -h, --help, --helpfull          Show this message and exit.
    ```

=== "user-management transfer"
    ```console
    (.cs_tools) C:\work\thoughtspot\cs_tools>cs_tools tools user-management transfer --help

    Usage: cs_tools tools user-management transfer --config IDENTIFIER [--option, ..., --help]

      Transfer ownership of objects from one User to another.

      Tags and GUIDs constraints are applied in OR fashion.

    Options:
      --from TEXT             username of the current content owner  (required)
      --to TEXT               username to transfer content to  (required)
      --tag TEXT              if specified, only move content marked with one or more of these tags
      --guids TEXT            if specified, only move specific objects
      --config IDENTIFIER     config file identifier  (required)
      -h, --help, --helpfull  Show this message and exit.
    ```

---

## Changelog

!!! tldr ":octicons-tag-16: v1.2.0 &nbsp; &nbsp; :material-calendar-text: 2022-04-28"

    === ":hammer_and_wrench: &nbsp; Added"
        - migrated [User Tools][tsut]{ target='secondary' .external-link } to CS Tools under `sync`
        - added user renaming as `rename`

    === ":wrench: &nbsp; Modified"
        - input/output using syncers! [@boonhapus][contrib-boonhapus]{ target='secondary' .external-link }.

??? info "Changes History"

    ??? tldr ":octicons-tag-16: v1.1.0 &nbsp; &nbsp; :material-calendar-text: 2021-11-01"

        === ":hammer_and_wrench: &nbsp; Added"
            - support for limited transfer of objects identified by GUID, or tag [@boonhapus][contrib-boonhapus]{ target='secondary' .external-link }.

        === ":wrench: &nbsp; Modified"
            - `--from` and `--to` options moved to required arugments

    ??? tldr ":octicons-tag-16: v1.0.0 &nbsp; &nbsp; :material-calendar-text: 2021-05-25"
        === ":hammer_and_wrench: &nbsp; Added"
            - Initial release [@boonhapus][contrib-boonhapus]{ target='secondary' .external-link }.

[contrib-boonhapus]: https://github.com/boonhapus
[tsut]: https://github.com/thoughtspot/user_tools
