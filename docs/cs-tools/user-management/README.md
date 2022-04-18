# User Management

This solution allows the customer to transfer objects from one user to another.

One use case for this tool is when an employee has left the company, but their
ThoughtSpot content needs to be saved. In this case, you may transfer all their created
content to another designated owner.

!!! caution "Compatibility Note"
    In the default case, transfer of owned content from one user to another is a one-shot operation. If your ThoughtSpot platform is on the __Latest Cloud__ release or the __Software 7.1.1__ release or newer, you can use the additional transfer options.

## CLI preview

=== "transfer-ownership --help"
    ```console
    (.cs_tools) C:\work\thoughtspot\cs_tools>cs_tools tools transfer-ownership --help

     Usage: cs_tools tools transfer-ownership [--version, --help] <command>

      Transfer ownership of all objects from one user to another.

    Options:
      --version   Show the version and exit.
      -h, --help  Show this message and exit.

    Commands:
      transfer  Transfer ownership of objects from one user to another.
    ```

=== "transfer-ownership transfer"
    ```console
    (.cs_tools) C:\work\thoughtspot\cs_tools>cstools tools transfer-ownership transfer --help

    Usage: cstools tools transfer-ownership transfer [--option, ..., --help] FROM TO

      Transfer ownership of objects from one user to another.

      Tags and GUIDs constraints are applied in OR fashion.

    Arguments:
      FROM  username of the current content owner  (required)
      TO    username to transfer content to  (required)

    Options:
      --tag TEXT    if specified, only move content marked with one or more of these tags
      --guids TEXT  if specified, only move specific objects
      --helpfull    Show the full help message and exit.
      -h, --help    Show this message and exit.
    ```

---

## Changelog

!!! tldr ":octicons-tag-16: v1.1.0 &nbsp; &nbsp; :material-calendar-text: 2021-11-01"

    === ":hammer_and_wrench: &nbsp; Added"
        - support for limited transfer of objects identified by GUID, or tag [@boonhapus][contrib-boonhapus]{ target='secondary' .external-link }.

    === ":wrench: &nbsp; Modified"
        - `--from` and `--to` options moved to required arugments

??? info "Changes History"

    ??? tldr ":octicons-tag-16: v1.0.0 &nbsp; &nbsp; :material-calendar-text: 2021-05-25"
        === ":hammer_and_wrench: &nbsp; Added"
            - Initial release [@boonhapus][contrib-boonhapus]{ target='secondary' .external-link }.

[keep-a-changelog]: https://keepachangelog.com/en/1.0.0/
[semver]: https://semver.org/spec/v2.0.0.html
[contrib-boonhapus]: https://github.com/boonhapus
