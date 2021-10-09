# Transfer Ownership

This solution allows the customer to transfer all objects from one user to another.

This is a very simple tool. The API call it uses will __only__ transfer all objects from
one single user to another single user.

One use case for this tool is when an employee has left the company, but their
ThoughtSpot content needs to be saved. In this case, you may transfer all their created
content to another designated owner.

## CLI preview

=== "transfer-ownership --help"
    ```console
    (.cs_tools) C:\work\thoughtspot\cs_tools>cs_tools tools transfer-ownership --help
    Usage: cs_tools tools transfer-ownership [OPTIONS] COMMAND [ARGS]...

      Transfer ownership of all objects from one user to another.

    Options:
      --version   Show the tool's version and exit.
      --helpfull  Show the full help message and exit.
      -h, --help  Show this message and exit.

    Commands:
      transfer  Transfer ownership of all objects from one user to another.
    ```

=== "transfer-ownership transfer"
    ```console
    (.cs-tools) C:\work\thoughtspot\cs_tools>cs_tools tools transfer-ownership transfer --help

    Usage: cs_tools tools transfer-ownership transfer [OPTIONS]

      Transfer ownership of all objects from one user to another.

    Options:
      --from TEXT  username of the current content owner  (required)
      --to TEXT    username to transfer content to  (required)
      --helpfull   Show the full help message and exit.
      -h, --help   Show this message and exit.
    ```
