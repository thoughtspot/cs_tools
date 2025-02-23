---
icon: material/database
hide:
  - toc
---

!!! note "Parameters"

    __This Syncer inherits all its parameters from the__{ .fc-blue } [__Trino Syncer__](./trino.md).
    
    :cstools-mage: __Starburst is basically a services layer on top of Trino.__{ .fc-purple }


??? question "How do I use the Syncer in commands?"

    __CS Tools__ accepts syncer definitions in either declarative or configuration file form.

    <sub class=fc-blue>Find the copy button :material-content-copy: to the right of the code block.</sub>

    === ":mega: &nbsp; Declarative"

        Simply write the parameters out alongside the command.

        ```bash
        cs_tools tools searchable metadata --syncer "starburst://host=thoughtspot.cloud.starburst.io&catalog=thoughtspot&schema=cs_tools&authentication=basic&username=tsadmin&secret=[redacted]" --config dogfood
        ```

        <sup class=fc-gray><i>* when declaring multiple parameters inline, you should <b class=fc-purple>wrap the enter value</b> in quotes.</i></sup>

    === ":recycle: &nbsp; Configuration File"

        1. Create a file with `.toml` extension.

            ??? abstract "syncer-overwrite.toml"
                ```toml
                [configuration]
                host = "thoughtspot.cloud.starburst.io"
                port = 8080
                catalog = "thoughtspot"
                schema = "cs_tools"
                authentication = "basic"
                username = "tsadmin"
                secret = "[redacted]"
                load_strategy = "TRUNCATE"
                ```
                <sup class=fc-gray><i>* this is a complete example, not all parameters are <b class=fc-red>required</b>.</i></sup>

        2. Reference the filename in your command in place of the parameters.

            ```bash
            cs_tools tools searchable metadata --syncer starburst://syncer-overwrite.toml --config dogfood
            ```

[cs-tools-serverless]: ../../getting-started/#__tabbed_1_4
[syncer-manifest]: https://github.com/thoughtspot/cs_tools/blob/master/cs_tools/sync/starburst/MANIFEST.json