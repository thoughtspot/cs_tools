---
icon: material/file
hide:
  - toc
---

!!! note "Parameters"

    ### __Required__ parameters are in __red__{ .fc-red } and __Optional__ parameters are in __blue__{ .fc-blue }.
    
    ---

    - [x] __directory__{ .fc-red }, *the folder location to write JSON files to*

    ---

    - [ ] __encoding__{ .fc-blue }, *whether or not to accept double-byte characters, like japanese or cryillic*
    <br />__default__{ .fc-gray }: `None` ( __allowed__{ .fc-green }: `UTF-8` )

    ---

    - [ ] __indentation__{ .fc-blue }, *the number of spaces to indent when writing to a file, used for pretty-printing data*
    <br />__default__{ .fc-gray }: `None` ( the json structure will be flat )


??? question "How do I use the Syncer in commands?"

    __CS Tools__ accepts syncer definitions in either declarative or configuration file form.

    <sub class=fc-blue>Find the copy button :material-content-copy: to the right of the code block.</sub>

    === ":mega: &nbsp; Declarative"

        Simply write the parameters out alongside the command.

        ```bash
        cs_tools tools searchable metadata --syncer "json://directory=." --config dogfood
        ```

        <sup class=fc-gray><i>* when declaring multiple parameters inline, you should <b class=fc-purple>wrap the enter value</b> in quotes.</i></sup>

    === ":recycle: &nbsp; Configuration File"

        1. Create a file with the `.toml` extension.

            ??? abstract "syncer-overwrite.toml"
                ```toml
                [configuration]
                directory = "."
                encoding = "UTF-8"
                indentation = 2
                ```
                <sup class=fc-gray><i>* this is a complete example, not all parameters are <b class=fc-red>required</b>.</i></sup>

        2. Write the filename in your command in place of the parameters.

            ```bash
            cs_tools tools searchable metadata --syncer json://syncer-overwrite.toml --config dogfood
            ```