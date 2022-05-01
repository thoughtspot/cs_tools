# Remote tsload

This solution allows you to interact with the tsload utility from a remote machine.
Loading data to ThoughtSpot using this tool happens over an HTTPS connection and thus,
all traffic is encrypted.

Data loads happen asynchronously. This means that the `file` command will begin a data
load and return once the data has been sent over to the remote server. This data must be
then committed to Falcon (which can take time depending on data size). The `file`
command will take care of all of this for you. You may check the status of the data load
with the returned cycle id and the `status` command.

??? important "Remote tsload enforces privileges"

    <span class=fc-coral>You __must__ have at least the __`Can Manage Data`__ privilege
    in ThoughtSpot to use this tool.</span>

    If you are running `tsload` within on the backend command line, you are most likely
    signed in under the `admin` account. __CS Tools__ enhances this security by
    enforcing privileges based on what user is logged in.


## CLI preview

=== "rtsload --help"
    ```console
    (.cs_tools) C:\work\thoughtspot\cs_tools>cs_tools tools rtsload --help
    Usage: cs_tools tools rtsload [--version, --help] <command>

      Enable loading files to ThoughtSpot from a remote machine.

      For further information on tsload, please refer to:
        https://docs.thoughtspot.com/latest/admin/loading/load-with-tsload.html
        https://docs.thoughtspot.com/latest/reference/tsload-service-api-ref.html
        https://docs.thoughtspot.com/latest/reference/data-importer-ref.html

    Options:
      --version               Show the version and exit.
      -h, --help, --helpfull  Show this message and exit.

    Commands:
      file    Load a file using the remote tsload service.
      status  Get the status of a data load.
    ```

=== "rtsload file"
    ```console
    (.cs_tools) C:\work\thoughtspot\cs_tools>cs_tools tools rtsload file --help

    Usage: cs_tools tools rtsload file --config IDENTIFIER [--option, ..., --help] FILE.csv

      Load a file using the remote tsload service.

    Arguments:
      FILE.csv  path to file to execute  (required)

    Options:
      --target_database TEXT          specifies the target database into which tsload should load the data  (required)
      --target_table TEXT             specifies the target database  (required)
      --target_schema TEXT            specifies the target schema  (default: falcon_default_schema)
      --empty_target / --noempty_target
                                      data in the target table is to be removed before the new data is loaded (default:
                                      --noempty_target)
      --max_ignored_rows INTEGER      maximum number of rows that can be ignored for successful load. If number of ignored rows exceeds
                                      this limit, the load is aborted  (default: 0)
      --date_format TEXT              format string for date values, accepts format spec by the strptime datetime library
                                      (default: %Y-%m-%d)
      --date_time_format TEXT         format string for datetime values, accepts format spec by the strptime datetime library
                                      (default: %Y-%m-%d %H:%M:%S)
      --time_format TEXT              format string for time values, accepts format spec by the strptime datetime library
                                      (default: %H:%M:%S)
      --skip_second_fraction          when true, skip fractional part of seconds: milliseconds, microseconds, or nanoseconds from either
                                      datetime or time values if that level of granularity is present in the source data
      --field_separator TEXT          field delimiter used in the input file  (default: |)
      --null_value TEXT               escape character in source data
      --boolean_representation TEXT   format in which boolean values are represented  (default: True_False)
      --has_header_row                indicates that the input file contains a header row
      --escape_character TEXT         specifies the escape character used in the input file  (default: ")
      --enclosing_character TEXT      enclosing character in csv source format  (default: ")
      --bad_records_file protocol://DEFINITION.toml
                                      file to use for storing rows that failed to load
      --config IDENTIFIER             config file identifier  (required)
      -h, --help, --helpfull          Show this message and exit.
    ```

=== "rtsload status"
    ```console
    (.cs_tools) C:\work\thoughtspot\cs_tools>cs_tools tools rtsload status --help

    Usage: cs_tools tools rtsload status --config IDENTIFIER [--option, ..., --help] CYCLE_ID

      Get the status of a data load.

    Arguments:
      CYCLE_ID  data load cycle id  (required)

    Options:
      --bad_records_file protocol://DEFINITION.toml
                                      file to use for storing rows that failed to load
      --config IDENTIFIER             config file identifier  (required)
      -h, --help, --helpfull          Show this message and exit.
    ```

---

## Changelog

!!! tldr ":octicons-tag-16: v1.2.0 &nbsp; &nbsp; :material-calendar-text: 2022-04-28"

    === ":wrench: &nbsp; Modified"
        - input/output using syncers! [@boonhapus][contrib-boonhapus]{ target='secondary' .external-link }.

??? info "Changes History"

    ??? tldr ":octicons-tag-16: v1.1.0 &nbsp; &nbsp; :material-calendar-text: 2021-11-08"
        === ":hammer_and_wrench: &nbsp; Added"
            - added many tsload flags [@boonhapus][contrib-boonhapus]{ target='secondary' .external-link }.
            - allow retrieval of bad records on failed data loads [@boonhapus][contrib-boonhapus]{ target='secondary' .external-link }.

    ??? tldr ":octicons-tag-16: v1.0.0 &nbsp; &nbsp; :material-calendar-text: 2021-05-22"
        === ":hammer_and_wrench: &nbsp; Added"
            - Initial release [@boonhapus][contrib-boonhapus]{ target='secondary' .external-link }.

---

[contrib-boonhapus]: https://github.com/boonhapus
