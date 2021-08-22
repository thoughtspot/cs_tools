# Delete Objects

**USE AT YOUR OWN RISK!**

**This tool uses private API calls which could change on any version update and break the tool.**

---

This tool allows the customer to delete common ThoughtSpot metadata from command line args or file input. 

Over the life of a ThoughtSpot cluster objects in the system grow. With changes in employee 
roles and business problems you may find that tens of thousands of objects can be left behind.
This tool allows you to remove objects from the metadata enmasse. 

The tool separates deletes objects in batches that can be specified in the args to speed up the delete process, but gives less visibility should an issue occur. A summary of what has been removed is saved in the logs directory of cs-tools. 


```console
(.cs_tools) C:\work\thoughtspot\cs_tools>cs_tools tools delete-objects --help

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
