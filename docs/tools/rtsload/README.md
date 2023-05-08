# Remote tsload

This solution allows you to interact with the tsload utility from a remote machine.
Loading data to ThoughtSpot using this tool happens over an HTTPS connection and thus,
all traffic is encrypted.

Data loads happen asynchronously. This means that the `file` command will begin a data
load and return once the data has been sent over to the remote server. This data must be
then committed to Falcon (which can take time depending on data size). The `file`
command will take care of all of this for you. You may check the status of the data load
with the returned cycle id and the `status` command.

??? info "Remote tsload enforces privileges"

    <span class=fc-coral>You __must__ have at least the __`Can Manage Data`__ privilege
    in ThoughtSpot to use this tool.</span>

    If you are running `tsload` within on the backend command line, you are most likely
    signed in under the `admin` account. __CS Tools__ enhances this security by
    enforcing privileges based on what user is logged in.


## CLI preview

=== "rtsload --help"
    ~cs~tools cs_tools tools rtsload --help

=== "rtsload file"
    ~cs~tools cs_tools tools rtsload file --help

=== "rtsload status"
    ~cs~tools cs_tools tools rtsload status --help

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
