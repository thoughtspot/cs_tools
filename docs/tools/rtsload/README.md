---
hide:
    - toc
---

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
    ~cs~tools ../.. cs_tools tools rtsload --help

=== "rtsload file"
    ~cs~tools ../.. cs_tools tools rtsload file --help

=== "rtsload status"
    ~cs~tools ../.. cs_tools tools rtsload status --help

[contrib-boonhapus]: https://github.com/boonhapus
