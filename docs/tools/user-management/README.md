---
hide:
    - toc
---

# User Management

Users and Groups can be managed on an individual basis in the Admin panel of your
__ThoughtSpot__ platform. Users may also be onboarded automatically upon successful
authentication with one of our supported Identity Providers. However, bulk management of
users otherwise is often difficult or requirements scripting.

These User Management tools will help you migrate users, sync them from external source
systems, or transfer all content from one user to another. All of which are common
activities when onboarding or offboarding many users at once.


## CLI preview

=== "user-management --help"
    ~cs~tools tools user-management --help

=== "user-management delete"
    ~cs~tools tools user-management delete --help

=== "user-management sync"
    ~cs~tools tools user-management sync --help

=== "user-management transfer"
    ~cs~tools tools user-management transfer --help

[contrib-boonhapus]: https://github.com/boonhapus
[tsut]: https://github.com/thoughtspot/user_tools
