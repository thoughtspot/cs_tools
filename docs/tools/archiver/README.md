---
hide:
    - toc
---

# Archiver

Archiver allows the ThoughtSpot admin to survey and identify all the content that users
create. This content can build up over time and cause maintenance and upgrades to run
more slowly. Additionally, your ThoughtSpot platform has some minor overhead when
holding references to all of these objects as well.

!!! danger "With great power, comes great responsibility!"

    Archiver is a tool that can perform mass modification and deletion of content in
    your platform! If not used appropriately, you could remove worthwhile answers and
    liveboards. __Your users trust you__, use this tool carefully.


## CLI preview

=== "archiver --help"
    ~cs~tools ../.. cs_tools tools archiver --help

=== "archiver identify"
    ~cs~tools ../.. cs_tools tools archiver identify --help

=== "archiver revert"
    ~cs~tools ../.. cs_tools tools archiver revert --help

=== "archiver remove"
    ~cs~tools ../.. cs_tools tools archiver remove --help

---

## Changelog

!!! tldr ":octicons-tag-16: v1.1.0 &nbsp; &nbsp; :material-calendar-text: 2022-04-28"

    === ":hammer_and_wrench: &nbsp; Added"
        - `archiver.identify` can now ignore existing tags [@boonhapus][contrib-boonhapus]{ target='secondary' .external-link }.

    === ":wrench: &nbsp; Modified"
        - input/output using syncers! [@boonhapus][contrib-boonhapus]{ target='secondary' .external-link }.
        - more sensible default parameters for identification

??? info "Changes History"

    ??? tldr ":octicons-tag-16: v1.0.0 &nbsp; &nbsp; :material-calendar-text: 2021-05-24"
        === ":hammer_and_wrench: &nbsp; Added"
            - Initial release [@boonhapus][contrib-boonhapus]{ target='secondary' .external-link }.

[contrib-boonhapus]: https://github.com/boonhapus
