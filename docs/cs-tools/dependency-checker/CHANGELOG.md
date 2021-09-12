---
hide:
  - toc
---

# Changelog

!!! info "Notable Changes"

    All notable changes to this tool will be documented in this file.

    The format is based on [Keep a Changelog][keep-a-changelog]{ target='secondary' .external-link }, and this project
    adheres to [Semantic Versioning][semver]{ target='secondary' .external-link }.

### :octicons-tag-16: v1.2.0 &nbsp; &nbsp; :material-calendar-text: 2021-09-11

=== ":hammer_and_wrench: &nbsp; Added"
    - support for column and formula dependents [@boonhapus][contrib-boonhapus]{ target='secondary' .external-link }.

=== ":wrench: &nbsp; Modified"
    - `ALTER TABLE` to support column dependencies [@boonhapus][contrib-boonhapus]{ target='secondary' .external-link }.
    - support for large clusters with API call batching [@boonhapus][contrib-boonhapus]{ target='secondary' .external-link }.

---

??? tldr ":octicons-tag-16: v1.1.0 &nbsp; &nbsp; :material-calendar-text: 2020-05-24"

    === ":wrench: &nbsp; Modified"
        - Migrated to new app structure [@boonhapus][contrib-boonhapus]{ target='secondary' .external-link }.


??? tldr ":octicons-tag-16: v1.0.1 &nbsp; &nbsp; :material-calendar-text: 2020-08-20"

    === ":no_entry_sign: &nbsp; Removed"
        - random `NotImplementedError` causing url creation to fail [@boonhapus][contrib-boonhapus]{ target='secondary' .external-link }.

    === ":bug: &nbsp; Bugfix"
        - url conversion for metadata types that don't have a GUID [@boonhapus][contrib-boonhapus]{ target='secondary' .external-link }.


??? tldr ":octicons-tag-16: v1.0.0 &nbsp; &nbsp; :material-calendar-text: 2020-08-15"

    === ":hammer_and_wrench: &nbsp; Added"
        - initial re-release [@boonhapus][contrib-boonhapus]{ target='secondary' .external-link }.


[keep-a-changelog]: https://keepachangelog.com/en/1.0.0/
[semver]: https://semver.org/spec/v2.0.0.html
[contrib-boonhapus]: https://github.com/boonhapus
