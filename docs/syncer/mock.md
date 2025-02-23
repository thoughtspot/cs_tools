---
icon: material/database-search
hide:
  - toc
---

!!! note "Parameters"

    __This Syncer does not take any parameters.__{ .fc-blue }
    
    It will only output SQL-like `CREATE TABLE` statements so that you can manually tweak them and create your own tables.


!!! question "How do I use the Syncer in commands?"

    __CS Tools__ accepts syncer definitions in either declarative or configuration file form.

    <sub class=fc-blue>Find the copy button :material-content-copy: to the right of the code block.</sub>

    === ":mega: &nbsp; Declarative"

        Simply write the parameters out alongside the command.

        ```bash
        cs_tools tools searchable metadata --syncer "mock://" --config dogfood
        ```

        <sup class=fc-gray><i>* when declaring multiple parameters inline, you should <b class=fc-purple>wrap the enter value</b> in quotes.</i></sup>

    === ":recycle: &nbsp; Configuration File"

        Why would you want to do this? :smile:
