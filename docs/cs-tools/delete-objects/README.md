# Delete Objects

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
in if supplied to `delete-objects from-file`

!!! note "Example input files"

    [:fontawesome-solid-file-excel: Excel template](template.xlsx)
     &nbsp; &nbsp; &nbsp; &nbsp; 
    [:fontawesome-solid-file-csv: CSV template](template.csv)


| type                 | guid                                 |
| -------------------- | ------------------------------------ |
| pinboard             | 1234a5bc-6d7e-8f90-12g3-h4ij5km6n78p |
| saved answer         | 1abcdef2-345g-6ghi-j789-0k1m2n345p67 |
| saved answer         | 1ab23456-789c-0de1-f23g-45h678ij9012 |
| pinboard             | ab1cde23-45f6-7gf8-hi90-1234j5k6789m |
| saved answer         | a1bc2d3e-f456-78g9-012h-3i4j5k67m890 |
| ...                  | ...                                  |
| PINBOARD_ANSWER_BOOK | 1234a5bc-6d7e-8f90-12g3-h4ij5km6n78p |
| QUESTION_ANSWER_BOOK | 1abcdef2-345g-6ghi-j789-0k1m2n345p67 |
| QUESTION_ANSWER_BOOK | 1ab23456-789c-0de1-f23g-45h678ij9012 |
| PINBOARD_ANSWER_BOOK | ab1cde23-45f6-7gf8-hi90-1234j5k6789m |
| QUESTION_ANSWER_BOOK | a1bc2d3e-f456-78g9-012h-3i4j5k67m890 |

```console
(.cs_tools) C:\work\thoughtspot\cs_tools>cs_tools tools delete-objects

Usage: cs_tools tools delete-objects [OPTIONS] COMMAND [ARGS]...

  Bulk delete metadata objects from your ThoughtSpot platform.

  USE AT YOUR OWN RISK! This tool uses private API calls which could change on any version update and
  break the tool.

  Leverages the /metadata/delete private API endpoint.

  Tool takes an input file and or a specific object and deletes it from the metadata.

  Valid metadata object type values are:
      - saved answer
      - pinboard

  CSV/XLSX file format should look like..

      +----------+-------+
      |  type    | guid  |
      +----------+-------+
      | answer   | guid1 |
      | pinboard | guid2 |
      | ...      | ...   |
      | answer   | guid3 |
      +----------+-------+

Options:
  --version   Show the tool's version and exit.
  --helpfull  Show the full help message and exit.
  -h, --help  Show this message and exit.

Commands:
  from-file      Remove many objects from ThoughtSpot.
  generate-file  Generates example file in Excel or CSV format
  single         Removes a specific object from ThoughtSpot.
```
