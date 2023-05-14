---
hide:
    - toc
---

# Configuration Files

__CS Tools__ is built on top of the __ThoughtSpot__ [REST APIs][ts-rest-apis].

In order to interact with the APIs, __ThoughtSpot__ enforces that you must log in as an Authorized User. If you do not
have a local account in __ThoughtSpot__ already, you can create one to use with __CS Tools__ as a service account[^1].

Whatever permissions this User has, will be the same security context that __CS Tools__ utilizes.

~cs~tools ../.. cs_tools config create --help


## Set up a config file

The command we'll use to set up a new config is `cs_tools config create`. This comes with many options, explore them
below.

=== "config"
    __[required]__{ .fc-red }

    `--config non-prod`

    The name of your configuration file. This can be whatever you want it to be. It's recommended to use dashes instead
    of spaces.

    __This name will be referenced in each of the tools' commands.__

=== "host, port"
    __[required]__{ .fc-red }

    `--host https://my-company.thoughtspot.cloud/`

    The URL of your __ThoughtSpot__ cluster. This is the same way that your users access __ThoughtSpot__. Make sure to
    include the `http://` scheme part of the url. `--port` can be specified if your instance lives on an alternate
    resource.

=== "username, password"
    __[required]__{ .fc-red }

    `--username cs_tools`

    Username and password of the local account to access __ThoughtSpot__ with.

    <span class=fc-coral>__If the password is not supplied__</span>, you'll be securely prompted to enter it before the
    config is finalized.

=== "default"
    __[optional]__{ .fc-purple }

    `--default`
    
    If supplied, designate this configuration as the one to use for tools' commands.

=== "syncer"
    __[optional]__{ .fc-purple }

    `--syncer protocol://DEFINITION.toml`

    Set default syncers within your configuration file. This can be supplied multiple times, once for each type of
    syncer.

    __You'll learn more about syncers later in this tutorial.__{ .fc-purple }

=== "disable_sso"
    __[optional]__{ .fc-purple }

    `--disable_sso`

    If your __ThoughtSpot__ cluster has automatic redirect enabled for your SAML or OIDC provider, supply this flag to
    disable it for the __CS Tools__ login experience.

=== "disable_ssl"
    __[optional]__{ .fc-purple }

    `--disable_ssl`

    Python performs a local verification check of SSL certificates. This can sometimes produces errors if the SSL cert
    is self-signed or if it is improperly applied to the domain your __ThoughtSpot__ cluster lives at. You can supply
    this flag to disable the verification check.

=== "verbose"
    __[optional]__{ .fc-purple }

    `--verbose`

    __CS Tools__ will log information to a file whenever you run commands. By default, low-level information is not
    stored in this file. Use the `--verbose` flag to capture more information when debugging issues.

    __This flag may be supplied to any tool command to override the behavior in your config file.__

=== "temp_dir"
    __[optional]__{ .fc-purple }

    `--temp_dir //172.16.0.10/cs_tools/tmp`

    __CS Tools__ sometimes uses the local filesystem as a temporary storage mechanism for large files. If you are
    running the tools on a resource-constrained platform, you can choose to write those files off-disk instead. Connect
    a network attached storage, and reference it with this option.

    __This flag may be supplied to any tool command to override the behavior in your config file.__

---

=== ":fontawesome-brands-windows: Windows"

    <sub class=fc-blue>Find the copy button :material-content-copy: to the right of the code block.</sub>
    ```powershell
    cs_tools config create `
      --config non-prod `
      --username cs_tools `
      --disable_sso `
      --default
    ```

=== ":fontawesome-brands-apple: :fontawesome-brands-linux: :material-application-braces-outline: Mac, Linux, ThoughtSpot cluster"

    <sub class=fc-blue>Find the copy button :material-content-copy: to the right of the code block.</sub>
    ```bash
    cs_tools config create \
      --config non-prod \
      --username cs_tools \
      --disable_sso \
      --default
    ```


## Check your config

~cs~tools ../.. cs_tools config check --help


## Example Configuration File

You can view all the currently configured environments by using the `cs_tools config show` command. If a particular configuration is specified, you can view the contents of that file.

??? danger "What happens with my password?"

    For security reasons, your password lives obfuscated both in memory and the configuration file upon being captured by `cs_tools`. It is only decrypted once per run, when authorizing with your ThoughtSpot platform.

~cs~tools ../.. cs_tools config show --config non-prod --anonymous


## Exploring the Tools

With a configuration file set up, we're ready to explore all the utilities that come with __CS Tools__.

__In the next section__, we'll learn about the __Archiver__{ .fc-purple } tool and see how we can leverage it to keep
our __ThoughtSpot__ cluster clean while it grows.


[^1]:

    The __CS Tools__ project supports many versions of __ThoughtSpot__, but usage of the REST APIs is restricted in
    [certain scenarios][ts-rest-license-matrix]. Local Users, or Basic Auth, is unrestricted across all __ThoughtSpot__
    license types.

[ts-rest-apis]: https://developers.thoughtspot.com/docs/?pageid=rest-apis
[ts-rest-license-matrix]: https://developers.thoughtspot.com/docs/?pageid=license-feature-matrix
