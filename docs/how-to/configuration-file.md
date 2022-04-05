All of the CS Tools will interact with the ThoughtSpot API in some way. For nearly all calls, the API requires a form of authentication.

For example, the details you put into the login screen that's presented when you visit your ThoughtSpot platform are the same you could use for `cs_tools`. This would mean that all actions you perform in `cs_tools`, would look as if you performed them yourself in your web interface.

![thoughtspot-ui-login](login_screen.png)

??? note "Arguments on every CS Tool Command"

    Each tool utilizes the ThoughtSpot API, so a configuration must be set. You can see a listing of all available arguments at any time, using the `--helpfull` option.

    === "On every Command"
        ```
          Name              Type      Description
          --------------------------------------------------------------
          --config       |   TEXT    |  config file identifier
          --temp_dir    | DIRECTORY |  filepath to save large temporary files to
          --verbose     |   FLAG    |  enable verbose logging for this run only
        ```

    === "Defined by --config"
        ```
          Name              Type      Description
          ------------------------------------------------------------------------
          --host        |   TEXT    |  thoughtspot server
          --username    |   TEXT    |  username when logging into ThoughtSpot
          --password    |   TEXT    |  password when logging into ThoughtSpot
          --port        |  INTEGER  |  optional, port of the thoughtspot server
          --disable_ssl |   FLAG    |  disable SSL verification
          --disable_sso |   FLAG    |  disable automatic SAML redirect
          --temp_dir    | DIRECTORY |  filepath to save large temporary files to
          --verbose     |   FLAG    |  enable verbose logging for this run only
        ```


## Config File Commands

The top level `cs_tools config` command has a few subcommands. There can be any number of config files saved on your machine. There can also be any number of config files set up against a target instance. Additionally, you may set a default configuration if you choose not to pass `--config` to each command.

=== "config create"

    ```console
    (.cs_tools) C:\work\thoughtspot>cs_tools config create --help

    Usage: cs_tools config create --config IDENTIFIER [--option, ..., --help]

      Create a new config file.

    Options:
      --config TEXT           config file identifier  (required)
      --host TEXT             thoughtspot server  (required)
      --port INTEGER          optional, port of the thoughtspot server
      --username TEXT         username when logging into ThoughtSpot  (required)
      --password TEXT         password when logging into ThoughtSpot  (required)
      --temp_dir DIRECTORY    location on disk to save temporary files
      --disable_ssl           disable SSL verification
      --disable_sso           disable automatic SAML redirect
      --verbose               enable verbose logging by default
      --default               set as the default configuration
      -h, --help, --helpfull  Show this message and exit.
    ```

=== "config modify"

    ```console
    (.cs_tools) C:\work\thoughtspot>cs_tools config modify --help

    Usage: cs_tools config modify --config IDENTIFIER [--option, ..., --help]

      Modify an existing config file.

    Options:
      --config TEXT                   config file identifier  (required)
      --host TEXT                     thoughtspot server
      --port INTEGER                  optional, port of the thoughtspot server
      --username TEXT                 username when logging into ThoughtSpot
      --password TEXT                 password when logging into ThoughtSpot
      --temp_dir DIRECTORY            location on disk to save temporary files
      --disable_ssl / --no-disable_ssl
                                      disable SSL verification
      --disable_sso / --no-disable_sso
                                      disable automatic SAML redirect
      --verbose / --normal            enable verbose logging by default
      --default                       set as the default configuration
      -h, --help, --helpfull          Show this message and exit.
    ```

=== "config delete"

    ```console
    (.cs_tools) C:\work\thoughtspot>cs_tools config delete --help

    Usage: cs_tools config delete --config IDENTIFIER [--option, ..., --help]

      Delete a config file.

    Options:
      --config TEXT           config file identifier  (required)
      -h, --help, --helpfull  Show this message and exit.
    ```

=== "config show"

    ```console
    (.cs_tools) C:\work\thoughtspot>cs_tools config show --help

    Usage: cs_tools config show --config IDENTIFIER [--option, ..., --help]

      Display the currently saved config files.

    Options:
      --config TEXT           optionally, display the contents of a particular config
      -h, --help, --helpfull  Show this message and exit.
    ```

## Example Configuration File

You can view all the currently configured environments by using the `cs_tools config show` command. If a particular configuration is specified, you can view the contents of that file.

??? danger "What happens with my password?"
    
    For security reasons, your password lives obfuscated both in memory and the configuration file upon being captured by `cs_tools`. It is only decrypted once per run, when authorizing with your ThoughtSpot platform.

`> cs_tools config show --config production`

```toml

Cluster configs located at: ~/.config/cs_tools

[default]
~/.config/cs_tools/cluster-cfg_production.toml

verbose = false
temp_dir = "/export/sdbc1/data/dump"

[thoughtspot]
host = "https://ts.thoughtspot.cloud"
disable_ssl = true
disable_sso = false

[auth.frontend]
username = "namey.namerson@thoughtspot.com"
password = "aBcDEf1GhIJkLMnOPQRStuVx"
```
