# Bulk Deleter

Over the life of a ThoughtSpot cluster objects in the system grow. With changes in
employee roles and business problems you may find that tens of thousands of objects can
be left behind. This tool allows you to remove objects from the metadata enmasse. 

The tool separates deletes objects in batches that can be specified in the args to speed
up the delete process, but gives less visibility should an issue occur. A summary of
what has been removed is saved in the logs directory of cs-tools. 

=== "bulk-deleter --help"
    ~cs~tools cs_tools tools bulk-deleter --help

=== "bulk-deleter single"
    ~cs~tools cs_tools tools bulk-deleter single --help

=== "bulk-deleter from-tabular"
    ~cs~tools cs_tools tools bulk-deleter from-tabular --help

---

## Changelog

!!! tldr ":octicons-tag-16: v1.1.0 &nbsp; &nbsp; :material-calendar-text: 2022-04-28"

    === ":wrench: &nbsp; Modified"
        - input/output using syncers! [@boonhapus][contrib-boonhapus]{ target='secondary' .external-link }.
        - updated to accept Liveboards

    === ":bug: &nbsp; Bugfix"
        - handle case where user submits an invalid object to be deleted (by type or guid)

??? info "Changes History"

    ??? tldr ":octicons-tag-16: v1.0.1 &nbsp; &nbsp; :material-calendar-text: 2021-11-09"
        === ":wrench: &nbsp; Modified"
            - now known as Bulk Deleter, `bulk-deleter`
            - `--save_path` is now `--export` [@boonhapus][contrib-boonhapus]{ target='secondary' .external-link }.

    ??? tldr ":octicons-tag-16: v1.0.0 &nbsp; &nbsp; :material-calendar-text: 2021-08-24"
        === ":hammer_and_wrench: &nbsp; Added"
            - Initial release from [@dpm][contrib-dpm]{ target='secondary' .external-link }.

---

[contrib-boonhapus]: https://github.com/boonhapus
[contrib-dpm]: https://github.com/DevinMcPherson-TS
