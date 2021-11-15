# Bulk Deleter

!!! caution "USE AT YOUR OWN RISK!"

    *__This tool uses private API calls!__ These could change with any version update and
    break the provided functionality.*

This tool allows the customer to delete common ThoughtSpot metadata from command line
args or file input. 

Over the life of a ThoughtSpot cluster objects in the system grow. With changes in
employee roles and business problems you may find that tens of thousands of objects can
be left behind. This tool allows you to remove objects from the metadata enmasse. 

The tool separates deletes objects in batches that can be specified in the args to speed
up the delete process, but gives less visibility should an issue occur. A summary of
what has been removed is saved in the logs directory of cs-tools. 

An example data set is provided below. This is the same format an Excel or CSV should be
in if supplied to `bulk-deleter from-file`

!!! note "Example input files"

    [:fontawesome-solid-file-excel: Excel template](template.xlsx)
     &nbsp; &nbsp; &nbsp; &nbsp; 
    [:fontawesome-solid-file-csv: CSV template](template.csv)

=== "bulk-deleter --help"
    ```console
    (.cs_tools) C:\work\thoughtspot\cs_tools>cs_tools tools bulk-deleter --help

     Usage: cs_tools tools bulk-deleter [--version, --help] <command>

      Bulk delete metadata objects from your ThoughtSpot platform.

      USE AT YOUR OWN RISK! This tool uses private API calls which could change on any
      version update and break the tool.

    Options:
      --version   Show the version and exit.
      -h, --help  Show this message and exit.

    Commands:
      from-file      Remove many objects from ThoughtSpot.
      generate-file  Generates example file in Excel or CSV format.
      single         Removes a specific object from ThoughtSpot.
    ```

=== "bulk-deleter from-file"
    ```console
    (.cs_tools) C:\work\thoughtspot\cs_tools>cs_tools tools bulk-deleter from-file --help

    Usage: cs_tools tools bulk-deleter from-file [--option, ..., --help] FILE.csv

      Remove many objects from ThoughtSpot.

      Accepts an Excel (.xlsx) file or CSV (.csv) file.

      CSV/XLSX file format should look like..

          +----------------+-------+
          | type           | guid  |
          +----------------+-------+
          | saved answer   | guid1 |
          | pinboard       | guid2 |
          | ...            | ...   |
          | saved answer   | guid3 |
          +----------------+-------+

    Arguments:
      FILE.csv  path to a file with columns "type" and "guid"  (required)

    Options:
      --batchsize INTEGER  maximum amount of objects to delete simultaneously
                           (default: 1)

      --helpfull           Show the full help message and exit.
      -h, --help           Show this message and exit.
    ```

=== "bulk-deleter generate-file"
    ```console
    (.cs_tools) C:\work\thoughtspot\cs_tools>cs_tools tools bulk-deleter generate-file --help

    Usage: cs_tools tools bulk-deleter generate-file [--option, ..., --help]

      Generates example file in Excel or CSV format.

    Options:
      --export FILE.csv  filepath to save generated file to  (required)
      --helpfull         Show the full help message and exit.
      -h, --help         Show this message and exit.
    ```

=== "bulk-deleter single"
    ```console
    (.cs_tools) C:\work\thoughtspot\cs_tools>cs_tools tools bulk-deleter single --help

    Usage: cs_tools tools bulk-deleter single [--option, ..., --help]

      Removes a specific object from ThoughtSpot.

    Options:
      --type (pinboard|PINBOARD_ANSWER_BOOK|saved answer|QUESTION_ANSWER_BOOK)
                                      type of the metadata to delete  (required)
      --guid TEXT                     guid to delete  (required)
      --helpfull                      Show the full help message and exit.
      -h, --help                      Show this message and exit.
    ```
