---
hide:
    - toc
---

# Scriptability

??? warning "New Version 3.0"

    Version 3 of Scriptability is a major rewrite that is not backwards compatible.  It introduces a new folder structure for exports and imports, a new mapping file format, and strict naming conventions.   If you have older version of scriptability content you will need to re-export that content to use the new structure.

Scriptability allows user to simplify and automate the export and import of ThoughtSpot content via TML.

The following are the primary use cases for the scriptability tool:

1. Export content for version control in git or other version control system.
2. Migrate content between clusters and orgs.
3. Make multiple copies of content, such as creating variations for different customers.
4. Backing up content before deleting.

Scriptability has been tested with a variety of complex scenarios.  However, some scenarios may not have been tested for and fail.  Please provide feedback, new feature ideas, errors, and unsupported scenarios by entering a [new issue][gh-issue].

??? danger "__This tool creates and updates content.  Regular shapshots are recommended!__"

    When importing content, it is possisible to accidentally overwrite content or create 
    multiple copies of content when you didn't intend to, just by using the wrong parameters.
    You should make sure you have a snapshot prior to making large changes.

    It's also recommended that you use git or other version management system to track changes to the TML.

??? important "Scriptability enforces content rules"

    <span class=fc-coral>You __must__ have at least the __`Can Manage Data`__ privilege
    in ThoughtSpot to use scriptability.</span>

    When exporting TML, you will need content permissions to the content to be exported.  
    When importing the TML it will be created as the authenticated user from the configuration.

This version of `cs_tools scriptability` supports the following:

* All TML types _and_ connections can be exported and imported with or without related content
* You can specify the specific content to be exported and imported.
* Orgs are supported for those instances where it's being used.
* You can tag and share content after it's imported.
* You can get a list of the GUID mappings between environments.

!!! warning "Limitations"

    * All of the general [TML limitation](https://docs.thoughtspot.com/cloud/latest/tml#_limitations_of_working_with_tml_files) apply when using the scriptability tool.
    * Users without RLS or Admin privileges won't download RLS rules when exporting.  It is recommended to use highly privileged users when exporting TML. 
    * The author of new content is the user in the config file, not the original author.

    The following are some known issues when using the tool:

    * There are rare scenarios where there is content you can access, but not download.  In these cases you will get an error message.

    In general, any changes that break dependencies are likely to throw errors.

!!! info "Helpful Links"

    :gear: &nbsp; __[ThoughtSpot scriptability documentation](https://docs.thoughtspot.com/cloud/latest/scriptability){ target='secondary' .external-link }__

## CLI preview

=== "scriptability --help"
    ~cs~tools ../.. cs_tools tools scriptability --help

=== "scriptability connection-check"
    ~cs~tools ../.. cs_tools tools scriptability connection-check --help

=== "scriptability export"
    ~cs~tools ../.. cs_tools tools scriptability export --help

=== "scriptability import"
    ~cs~tools ../.. cs_tools tools scriptability import --help

=== "scriptability compare"
    ~cs~tools ../.. cs_tools tools scriptability compare --help

=== "scriptability tmlfs"
    ~cs~tools ../.. cs_tools tools scriptability tmlfs --help

=== "scriptability mapping"
    ~cs~tools ../.. cs_tools tools scriptability mapping --help

---

## Changelog

!!! tldr ":octicons-tag-16: v3.0.0 &nbsp; &nbsp; :material-calendar-text: 2022-09-12"
    === ":hammer_and_wrench: &nbsp; Major update with breaking changes"
    - Reworked the import and export commands to have simpler parameters.
    - Added a new TML file system with specific folders for each type of content along with new ands for working with the TML file system.
    - Added a new tool for view the GUID mapping with names and types.
    - Refactored the import code to be more modular and easier to maintain.
    - Multiple bug fixes.

??? info "Changes History"

    ??? tldr ":octicons-tag-16: v2.0.0 &nbsp; &nbsp; :material-calendar-text: 2023-05-08"
    === ":hammer_and_wrench: &nbsp; Added"
    - Import connections and SQL views
    - Support for Orgs
    - Updated mapping file format
    - Using new version of thoughtspot_tml
    - Multiple bug fixes

    ??? tldr ":octicons-tag-16: v1.4.1 &nbsp; &nbsp; :material-calendar-text: 2022-09-12"
        === ":hammer_and_wrench: &nbsp; Bug fixes"
            - Fixed an error that would stop download if SQL views were used in earlier versions of ThoughtSpot. A message will be displayed, but the export will continue.
            - Fixed an error where worksheets weren't downloaded when exporting based on a filters, such as tags or owner.

    ??? tldr ":octicons-tag-16: v1.4.0 &nbsp; &nbsp; :material-calendar-text: 2022-09-01"
        === ":hammer_and_wrench: &nbsp; Added"
            - Download tables and connections
            - Upload tables
            - Multiple bug fixes

    ??? tldr ":octicons-tag-16: v1.1.0 &nbsp; &nbsp; :material-calendar-text: 2022-07-19"
        === ":hammer_and_wrench: &nbsp; Added"
            - Create an empty mapping file
            - Compare two TML files
            - Create content with automatic dependency handling
            - Update content with automatic dependency handling  
            - Allow new and updated content to be shared with groups during import
            - Allow tags to be applied to new and updated content during import

    ??? tldr ":octicons-tag-16: v1.0.0 &nbsp; &nbsp; :material-calendar-text: 2022-04-15"
        === ":hammer_and_wrench: &nbsp; Added"
            - Initial release [@billdback-ts][contrib-billdback-ts]{ target='secondary' .external-link }.


---

[keep-a-changelog]: https://keepachangelog.com/en/1.0.0/
[gh-issue]: https://github.com/thoughtspot/cs_tools/issues/new/choose
[semver]: https://semver.org/spec/v2.0.0.html
[contrib-billdback-ts]: https://github.com/billdback-ts
