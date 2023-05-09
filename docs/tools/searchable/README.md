---
hide:
    - toc
---

<style>
  .tabbed-block ul ul ul { columns: 3; }
</style>

# Searchable Content

As your platform grows, it can oftentimes be useful to keep track of how much content
is created within the system. For example, tracking the amount of answers or liveboards
created over time can help you understand how your Users interact with __ThoughtSpot__.

Another use case might be to set up a liveboard gating conditions based on when or how
often a user uploads data (eg. a combination of metadata type of "imported data", the 
metadata object's modified/created time and the __ThoughtSpot__ datetime function
`today()`). This could give you early warning when a user is missing a dataset that could
provide value to others in your platform.

??? info "__ThoughtSpot__ Data Model"

    <figure markdown>
      ![searchable-erd](searchable-erd.png)
      <figcaption>__full schema diagram for the searchable ThoughtSpot metadata__</figcaption>
    </figure>
    

## CLI preview

=== "searchable --help"
    ~cs~tools ../.. cs_tools tools searchable --help

=== "searchable gather"
    ~cs~tools ../.. cs_tools tools searchable gather --help

=== "searchable bi-server"
    ~cs~tools ../.. cs_tools tools searchable bi-server --help

=== "searchable deploy"
    ~cs~tools ../.. cs_tools tools searchable deploy --help

---

## Changelog

!!! tldr ":octicons-tag-16: v1.3.0 &nbsp; &nbsp; :material-calendar-text: 2022-04-28"

    === ":wrench: &nbsp; Modified"
        - now known as simply Searchable, `searchable`
            - includes metadata about..
                - Tables
                - Views
                - Worksheets
                - Columns & Formulas
                - Answers
                - Liveboards
                - Dependencies
                - Users
                - Groups
                - Privileges
                - Tags
                - Access Control
                - TS: BI Server

??? info "Changes History"

    ??? tldr ":octicons-tag-16: v1.2.1 &nbsp; &nbsp; :material-calendar-text: 2021-11-09"
        === ":wrench: &nbsp; Modified"
            - now known as Searchable Content, `searchable-content`
            - `--save_path` is now `--export` [@boonhapus][contrib-boonhapus]{ target='secondary' .external-link }.
            - `tml` is now `spotapp` [@boonhapus][contrib-boonhapus]{ target='secondary' .external-link }.

    ??? tldr ":octicons-tag-16: v1.2.0 &nbsp; &nbsp; :material-calendar-text: 2021-09-11"
        === ":wrench: &nbsp; Modified"
            - `ALTER TABLE` to support column dependencies [@boonhapus][contrib-boonhapus]{ target='secondary' .external-link }.
            - support for large clusters with API call batching [@boonhapus][contrib-boonhapus]{ target='secondary' .external-link }.

    ??? tldr ":octicons-tag-16: v1.1.0 &nbsp; &nbsp; :material-calendar-text: 2021-05-25"
        === ":wrench: &nbsp; Modified"
            - Migrated to new app structure [@boonhapus][contrib-boonhapus]{ target='secondary' .external-link }.

    ??? tldr ":octicons-tag-16: v1.0.0 &nbsp; &nbsp; :material-calendar-text: 2020-08-18"
        === ":hammer_and_wrench: &nbsp; Added"
            - Initial re-release [@boonhapus][contrib-boonhapus]{ target='secondary' .external-link }.


[contrib-boonhapus]: https://github.com/boonhapus
