# Extractor

It is often difficult to programmatically use the result set of a query that runs in the
ThoughtSpot UI search bar. To use the data that we retrieve from a query
programmatically, you can use this tool to just that.

When issuing a query through the ThoughtSpot UI, users make selections to disambiguate
a query. Your Search will need to be modified in order to extract data from the source.
See [Components of a search query][search-components].


## CLI preview

=== "extractor --help"
    ~cs~tools cs_tools tools extractor --help

=== "extractor search"
    ~cs~tools cs_tools tools extractor search --help

---

## Changelog

!!! tldr ":octicons-tag-16: v1.1.0 &nbsp; &nbsp; :material-calendar-text: 2022-04-28"

    === ":wrench: &nbsp; Modified"
        - input/output using syncers! [@boonhapus][contrib-boonhapus]{ target='secondary' .external-link }.

??? info "Changes History"

    ??? tldr ":octicons-tag-16: v1.0.0 &nbsp; &nbsp; :material-calendar-text: 2020-11-14"
        === ":hammer_and_wrench: &nbsp; Added"
            - Initial release [@boonhapus][contrib-boonhapus]{ target='secondary' .external-link }.

---

[tsbi]: https://cloud-docs.thoughtspot.com/admin/system-monitor/worksheets.html#description-of-system-worksheets-and-views
[search-components]: https://developers.thoughtspot.com/docs/?pageid=rest-api-reference#_search_data
[contrib-boonhapus]: https://github.com/boonhapus
