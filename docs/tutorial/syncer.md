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

The syntax for defining a Syncer configuration (called a "definition file") is a simple URI, but it can be confusing at
first. All Syncers can take their arguments either in the form of a definition file, or directly on the command line.

!!! info inline end "Syncer Syntax"
    <b><span class=fc-purple>csv</span> :// <span class=fc-blue>/fullpath/to/your/configuration.toml</span></b>

    It's broken into 3 parts.. the <b class=fc-purple>protocol</b>, a separator, and the <b class=fc-blue>definition</b>.

To keep things simple, let's define a configuration for the CSV Syncer. This will allow us to export data that various
tools produce directly to a directory. You can find all the configuration settings for syncers in [their section of the
documentation][syncer-csv].

The CSV syncer is simple, all that's __required__{ .fc-coral } is the directory location to export data to. Follow the
instructions below to create a new CSV syncer.

Execute the following command in your terminal. This will create a new __report.toml__{ .fc-blue } file in your Downloads
folder.

=== ":fontawesome-brands-windows: Windows"

    === "Command Format"
        <sub class=fc-blue>Find the copy button :material-content-copy: to the right of the code block.</sub>
        ```powershell
        --syncer csv://directory=$env:USERPROFILE\\Downloads
        ```

    === "File Format"
        <sub class=fc-blue>Find the copy button :material-content-copy: to the right of the code block.</sub>
        ```toml
        [configuration]
        directory = "$env:USERPROFILE\\Downloads"
        ```

=== ":fontawesome-brands-apple: :fontawesome-brands-linux: :material-application-braces-outline: Mac, Linux, ThoughtSpot cluster"

    === "Command Format"
        <sub class=fc-blue>Find the copy button :material-content-copy: to the right of the code block.</sub>
        ```bash
        --syncer csv://directory=$HOME/Downloads
        ```

    === "File Format"
        <sub class=fc-blue>Find the copy button :material-content-copy: to the right of the code block.</sub>
        ```toml
        [configuration]
        directory = "$HOME/Downloads"
        ```

??? info "Full CSV Syncer definition example"

    ```toml
    # This is the top-level directive, it is required.
    [configuration]

    # The location to write CSVs to.
    directory = "/path/to/my/folder/"
    
    # Control what character is used to delimit values, CSV stands for
    # "commas separated values" but this parameter allows us to use
    # whatever character we want.
    delimiter = '|'
    
    # Control what character is used to escape reserved characters.
    escape_character = '\'
    
    # Whether to turn the DIRECTORY above into a zip file, or leave
    # exported data as CSV.
    zipped = true
    ```


## Specifying the Syncer

We've created a way for __CS Tools__ to export data to CSV, but how do we use it? Remember, __Archiver__{ .fc-purple }
has an option called `--syncer protocol://DEFINITION.toml`.

All __Syncers__{ .fc-blue } in __CS Tools__ follow a standard format, called a protocol. Additionally, each
__Syncer__{ .fc-blue } can be customized using their own set of parameters. For example, a __CSV Syncer__ and a
__Snowflake Syncer__ require different setup information to be used.

Whenever you need to specify a __Syncer__{ .fc-blue }, you'll do so by providing the __protocol name__{ .fc-purple }
followed by the __location of your syncer definition file__{ .fc-blue }, separated by the three characters `://`. This
is identical to the components that make up many common URI syntax like `https://`, `ftp://`, and `mailto://`.

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
    --syncer csv://directory=$env:USERPROFILE\\Downloads `
    --dry-run
    ```

=== ":fontawesome-brands-apple: :fontawesome-brands-linux: :material-application-braces-outline: Mac, Linux, ThoughtSpot cluster"

    <sub class=fc-blue>Find the copy button :material-content-copy: to the right of the code block.</sub>
    ```bash
    cs_tools tools archiver identify \
    --syncer csv://directory=$HOME/Downloads \
    --dry-run
    ```

If we look at the contents of the file that was dumped to our Downloads directory, we'll find details about all the
content that will be tagged and identified as inactive.

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
