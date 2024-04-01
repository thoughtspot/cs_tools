---
hide:
    - toc
---

<style>
  /* Make better use of whitespace for supported syncers */
  .admonition.tip > ul { columns: 3; }
</style>

# Learn about Syncers

__Syncers__{ .fc-blue } allow __CS Tools__ to interact with popular data storage formats without having to know the
details of how to do so. Think of it as a way to plug and play different places to store your data.

We'll define for __CS Tools__ which data storage we're using, and then pass that along with the rest of our command.

!!! tip "Formats that __CS Tools__ currently supports"

    - CSV
    - SQLite
    - __ThoughtSpot__ Falcon
    - Snowflake
    - Google BigQuery
    - Google Sheets

---

With __Archiver__{ .fc-purple }, we can supply a __Syncer__{ .fc-blue } by passing the `--syncer` option.

Along with the `--dry-run` option, this will allow to inspect the Answers and Liveboards that would be marked for
deletion, all without ever affecting the platform we're targeting.

<center>
![syncer-architecture](../assets/images/syncer-arch.svg){ width=85% }
</center>

---

## Set up the CSV Syncer

!!! info inline end "Syncer Syntax"
    <b><span class=fc-purple>csv</span> :// <span class=fc-blue>/filepath/to/your/configuration.toml</span></b>

    It's broken into 3 parts.. the <b class=fc-purple>protocol</b>, a separator, and the <b class=fc-blue>definition</b>.

The syntax for defining a Syncer configuration (called a "definition file") is like a local URL which defines all of the
information a Syncer needs to be able to operate properly. All Syncers can take their arguments either in the form of a
definition file, or directly on the command line.

To keep things simple, let's define a configuration for the __CSV__{ .fc-purple } Syncer. This will allow us to export
data that tools produce directly to a directory on your local machine. You can find all the configuration settings for
syncers in [their section of the documentation][syncer-csv].

The CSV syncer doesn't take many arguments, all that's __required__{ .fc-coral } is the directory location to save the
data to.

!!! tip ""
    === "Command Format"
        <sub class=fc-blue>Find the copy button :material-content-copy: to the right of the code block.</sub>
        ```powershell
        --syncer csv://directory=.
        ```

    === "File Format"
        <sub class=fc-blue>Find the copy button :material-content-copy: to the right of the code block.</sub>

        `definition.toml`

        ```toml
        [configuration]
        directory = "."
        ```

    This will save one or more CSVs in the current direction. The `.` means the __current working directory__ from where
    you are running the CS Tools command.


## Specifying the Syncer

We've created a way for __CS Tools__ to export data to CSV, but how do we use it? Remember, __Archiver__{ .fc-purple }
has an option called `--syncer protocol://DEFINITION.toml`.

All __Syncers__{ .fc-blue } in __CS Tools__ take their arguments a standard format, called a protocol. Additionally,
each __Syncer__{ .fc-blue } can be customized using their own set of parameters. For example, a __CSV Syncer__ and a
__Snowflake Syncer__ require different setup information to be used.

Whenever you need to specify a __Syncer__{ .fc-blue }, you'll do so by providing the __protocol name__{ .fc-purple }
followed by the __location of your syncer definition file__{ .fc-blue } or its arguments inline, separated by the three
characters `://`.

You can find the full details for each __Syncer__{ .fc-blue } definition, as well as their protocol name in our
[documentation][syncer-all].

!!! tip

    Since __Syncer__{ .fc-blue } definitions are just files, they can be referenced across multiple configurations or
    even stored in a centrally located directory and be leveraged by multiple users interacting with __CS Tools__.


## Try it out

Now that we've learned everything about how to use our CSV Syncer, let's try the command from the diagram above.

=== ":fontawesome-brands-windows: Windows"

    <sub class=fc-blue>Find the copy button :material-content-copy: to the right of the code block.</sub>
    ```powershell
    cs_tools tools archiver identify `
    --syncer csv://directory=. `
    --dry-run
    ```

=== ":fontawesome-brands-apple: :fontawesome-brands-linux: :material-application-braces-outline: Mac, Linux, ThoughtSpot cluster"

    <sub class=fc-blue>Find the copy button :material-content-copy: to the right of the code block.</sub>
    ```bash
    cs_tools tools archiver identify \
    --syncer csv://directory=. \
    --dry-run
    ```

If we look at the contents of the file that were dumped to our local directory, we'll find details about all the content
that will be tagged and identified as inactive.

| content_type | guid        | name         | created_at   | modified_at  | author              | operation |
| ------------ | ----------- | ------------ | ------------ | ------------ | ------------------- | --------- |
| answer       | 3d13b8e4-.. | ThoughtSpo.. | 3 months ago | 3 months ago | abc@thoughtspot.com | identify  |
| answer       | dc659672-.. | Accounts P.. | 3 months ago | 3 months ago | def@thoughtspot.com | identify  |
| answer       | 7c4916bc-.. | Customers .. | 3 months ago | 3 months ago | ghi@thoughtspot.com | identify  |
| answer       | cc623165-.. | Cohort Ans.. | 3 months ago | 3 months ago | jkl@thoughtspot.com | identify  |
| ...          | ...         | ...          | ...          | ...          | ...                 | ...       |


## Define a governance process

Now that we've got the tools to be able to maintain a clean __ThoughtSpot__ platform as it grows, it's an excellent idea
to regularly visit the state of metadata in our cluster.

__In the final section__, we'll explore ways to schedule the tools on both Windows and Unix platforms.


[syncer-all]: ../syncer/what-is.md
[syncer-csv]: ../syncer/csv.md
