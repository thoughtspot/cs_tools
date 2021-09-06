# Remote tsload

This solution allows the customer to interact with the tsload utility from a remote
machine. Loading data to ThoughtSpot using this tool happens over an HTTPS connection
and thus, all traffic is encrypted.

Data loads happen asynchronously. This means that the `file` command will begin a data
load and return once the data has been sent over to the remote server. This data must be
then committed to Falcon (which can take time depending on data size). The `file`
command will take care of all of this for you. You may check the status of the data load
with the returned cycle id and the `status` command.

A benefit of using remote tsload is that it encourages and enforces security. If you are
running tsload within the software command line, you are most likely signed in under the
`admin` account. Remote tsload enforces privileges: the logged in user **must** have at
least the "Can Manage Data" privilege in ThoughtSpot.

## CLI preview

```console
(.cs_tools) C:\work\thoughtspot\cs_tools>cs_tools tools rtsload

Usage: cs_tools tools rtsload [OPTIONS] COMMAND [ARGS]...

  Enable loading files to ThoughtSpot from a remote machine.

  For further information on tsload, please refer to:
    https://docs.thoughtspot.com/latest/admin/loading/load-with-tsload.html
    https://docs.thoughtspot.com/latest/reference/tsload-service-api-ref.html
    https://docs.thoughtspot.com/latest/reference/data-importer-ref.html

Options:
  --version   Show the tool's version and exit.
  --helpfull  Show the full help message and exit.
  -h, --help  Show this message and exit.

Commands:
  file    Load a file using the remote tsload service.
  status  Get the status of a data load.
```
