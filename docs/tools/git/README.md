---
hide:
    - toc
---

# Git (aka Version Control)

The `git` tool provides a command-line interface for using the git specific API endpoints in ThoughtSpot.

??? warning "v2.0 API calls"

    The `git` tool uses the v2.0 API calls.  Git calls were introduced in version 9.6.cl as beta and are fully released
    in 9.7.cl.  

These API endpoints allow you to create and manage configurations with GitHub and to 
commit and deploy changes to and from GitHub. These APIs are commonly used in environments where you want to develop content in one environment and
deploy to a different environment, such as another cluster or org.  

For more information see the 
[Git Integration and version control](https://developers.thoughtspot.com/docs/git-integration) in the documentation.

## CLI preview

=== "git --help"
    ~cs~tools tools git --help

## CLI Config Commands
=== "git config --help"
    ~cs~tools tools git config --help

=== "git config create --help"
    ~cs~tools tools git config create --help

=== "git config update --help"
    ~cs~tools tools git config update --help

=== "git config search --help"
    ~cs~tools tools git config search --help

## CLI Branches Commands
=== "git branches --help"
    ~cs~tools tools git branches --help

=== "git branches commit --help"
    ~cs~tools tools git branches commit --help

=== "git branches search-commits --help"
    ~cs~tools tools git branches search-commits --help

=== "git branches revert-commit --help"
    ~cs~tools tools git branches revert-commit --help

=== "git branches validate --help"
    ~cs~tools tools git branches validate --help

=== "git branches deploy --help"
    ~cs~tools tools git branches deploy --help

[keep-a-changelog]: https://keepachangelog.com/en/1.0.0/
[gh-issue]: https://github.com/thoughtspot/cs_tools/issues/new/choose
[semver]: https://semver.org/spec/v2.0.0.html
[contrib-billdback-ts]: https://github.com/billdback-ts
