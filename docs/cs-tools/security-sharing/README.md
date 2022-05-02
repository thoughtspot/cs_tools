# Security Sharing

This solution allows you to quickly manage column-level and table-level security models
within an easy to manipulate user interface.

Setting up Column Level Security (especially on larger tables) can be time-consuming
when done directly in the ThoughtSpot user interface. The web interface provided by this
tool will allow you to quickly understand the current security settings for a given
table across all columns, and as many groups as are in your platform. You may then set
the appropriate security settings for those group-table combinations.

## User Interface preview

![user-interface-gif](./application.gif)

## CLI preview

=== "security-sharing --help"
    ```console
    (.cs_tools) C:\work\thoughtspot\cs_tools>cs_tools tools security-sharing --help

     Usage: cs_tools tools security-sharing [--version, --help] <command>

      Scalably manage your table- and column-level security right in the browser.

      Setting up Column Level Security (especially on larger tables) can be
      time-consuming when done directly in the ThoughtSpot user interface. The web
      interface provided by this tool will allow you to quickly understand the current
      security settings for a given table across all columns, and as many groups as are
      in your platform. You may then set the appropriate security settings for those
      group-table combinations.

    Options:
      --version   Show the version and exit.
      -h, --help  Show this message and exit.

    Commands:
      run    Start the built-in webserver which runs the security management interface.
      share  Share database tables with groups.
    ```

=== "security-sharing run"
    ```console
    (.cs_tools) C:\work\thoughtspot\cs_tools>cs_tools tools security-sharing run --help

    Usage: cs_tools tools security-sharing run [--option, ..., --help]

      Start the built-in webserver which runs the security management interface.

    Options:
      --webserver-port INTEGER  port to host the webserver on  (default: 5000)
      --helpfull                Show the full help message and exit.
      -h, --help                Show this message and exit.
    ```

=== "security-sharing share"
    ```console
    (.cs_tools) C:\work\thoughtspot\cs_tools>cs_tools tools security-sharing share --help

    Usage: cs_tools tools security-sharing share [--option, ..., --help]

      Share database tables with groups.

    Options:
      --group TEXT                    group to share with  (required)
      --permission (view|edit|remove)
                                      permission type to assign  (required)
      --database TEXT                 name of database of tables to share  (required)
      --schema TEXT                   name of schema of tables to share
                                      (default: falcon_default_schema)

      --table TEXT                    name of the table to share, if not provided then
                                      share all tables

      --helpfull                      Show the full help message and exit.
      -h, --help                      Show this message and exit.
    ```

---

## Changelog


!!! tldr ":octicons-tag-16: v1.0.0 &nbsp; &nbsp; :material-calendar-text: 2021-08-17"

    === ":hammer_and_wrench: &nbsp; Added"
        - Initial release from [@mishathoughtspot][contrib-misha]{ target='secondary' .external-link }.

---

[contrib-misha]: https://github.com/MishaThoughtSpot
