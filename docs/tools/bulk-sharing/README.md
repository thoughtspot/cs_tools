# Bulk Sharing

This solution allows you to quickly manage column-level and table-level security models
within an easy to manipulate user interface.

Setting up Column Level Security (especially on larger tables) can be time-consuming
when done directly in the ThoughtSpot user interface. The web interface provided by this
tool will allow you to quickly understand the current security settings for a given
table across all columns, and as many groups as are in your platform. You may then set
the appropriate security settings for those group-table combinations.

## User Interface preview

![user-interface-gif](./application.gif)

## CLI preview

=== "bulk-sharing --help"
    ~cs~tools cs_tools tools bulk-sharing --help

=== "bulk-sharing cls-ui"
    ~cs~tools cs_tools tools bulk-sharing cls-ui --help

=== "bulk-sharing single"
    ~cs~tools cs_tools tools bulk-sharing single --help

---

## Changelog


!!! tldr ":octicons-tag-16: v1.0.0 &nbsp; &nbsp; :material-calendar-text: 2021-08-17"

    === ":hammer_and_wrench: &nbsp; Added"
        - Initial release from [@mishathoughtspot][contrib-misha]{ target='secondary' .external-link }.

---

[contrib-misha]: https://github.com/MishaThoughtSpot
