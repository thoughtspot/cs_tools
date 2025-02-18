---
hide:
    - toc
---

# Remote TQL

This solution allows you to interact with the TQL utility from a remote machine. There
are three command for remote TQL:

 - Interactive, get the full TQL experience on your local machine
 - Command, execute a single TQL command
 - File, execute a set of commands

??? info "Remote TQL enforces privileges"

    <span class=fc-coral>You __must__ have at least the __`Can Manage Data`__ privilege
    in ThoughtSpot to use this tool.</span>

    If you are running `TQL` within on the backend command line, you are most likely
    signed in under the `admin` account. __CS Tools__ enhances this security by
    enforcing privileges based on what user is logged in.

## Interactive TQL preview

![interactive-rtql](./interactive_rtql.png)

## CLI preview

=== "rtql --help"
    ~cs~tools tools rtql --help

=== "rtql interactive"
    ~cs~tools tools rtql interactive --help

[contrib-boonhapus]: https://github.com/boonhapus
