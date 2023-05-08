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
    ~cs~tools cs_tools tools user-management --help

=== "user-management rename"
    ~cs~tools cs_tools tools user-management rename --help

=== "user-management sync"
    ~cs~tools cs_tools tools user-management sync --help

=== "user-management transfer"
    ~cs~tools cs_tools tools user-management transfer --help

---

## Changelog

!!! tldr ":octicons-tag-16: v1.2.0 &nbsp; &nbsp; :material-calendar-text: 2022-04-28"

    === ":hammer_and_wrench: &nbsp; Added"
        - migrated [User Tools][tsut]{ target='secondary' .external-link } to __CS Tools__ under `sync`
        - added user renaming as `rename`

    === ":wrench: &nbsp; Modified"
        - input/output using syncers! [@boonhapus][contrib-boonhapus]{ target='secondary' .external-link }.

??? info "Changes History"

    ??? tldr ":octicons-tag-16: v1.1.0 &nbsp; &nbsp; :material-calendar-text: 2021-11-01"

        === ":hammer_and_wrench: &nbsp; Added"
            - support for limited transfer of objects identified by GUID, or tag [@boonhapus][contrib-boonhapus]{ target='secondary' .external-link }.

        === ":wrench: &nbsp; Modified"
            - `--from` and `--to` options moved to required arugments

    ??? tldr ":octicons-tag-16: v1.0.0 &nbsp; &nbsp; :material-calendar-text: 2021-05-25"
        === ":hammer_and_wrench: &nbsp; Added"
            - Initial release [@boonhapus][contrib-boonhapus]{ target='secondary' .external-link }.

[contrib-boonhapus]: https://github.com/boonhapus
[tsut]: https://github.com/thoughtspot/user_tools
