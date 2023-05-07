# Scriptability

This tool allows user to simplify and automate the export and import of ThoughtSpot TML from and to the same or different instances.

There are several use cases where exporting and importing TML is useful:

1. Export TML for version control.
2. Export TML for migration to a different ThoughtSpot instance.
3. Export TML to modify and create copies, such as for different customers or in different languages.

??? danger "__This tool creates and updates content.  Regular shapshots are recommended!__"

    When importing content, it is possisible to accidentally overwrite content or create 
    multiple copies of content when you didn't intend to, just by using the wrong parameters.
    You should make sure you have a snapshot or backup prior to making large changes.

??? important "Scriptability enforces content rules"

    <span class=fc-coral>You __must__ have at least the __`Can Manage Data`__ privilege
    in ThoughtSpot to use this tool.</span>

    When exporting the TML, you will need content permissions to the content to be exported.  
    When importing the TML it will be created as the authenticated user of the tool.

This version of `cs_tools scriptability` supports the following:

* All TML types _and_ connections can be exported and imported with or without related content
* Orgs are now supported for those instances where it's being used.

__Export__

* Export TML based on a GUID
* Export TML based on the author
* Export TML based on a ThoughtSpot TAG
* Export only TML that matches a pattern

__Import__

* Import TML (update and create new) with complex dependency handling (updated)
* Share and tag content when importing

__Compare__

* Compare two TML files for differences

!!! warning "TML is complex and this tool is new."

    The scriptability tool has been tested in a number of complex scenarios.  But TML export and import is 
    complex with a variety of different scenarios.  It is anticipated that some scenarios have not been 
    tested for and won't work.  Please provide feedback on errors and unsupported scenarios by 
    entering a [new issue][gh-issue].

!!! warning "Limitations"

    * All of the general [TML limitation](https://docs.thoughtspot.com/software/latest/tml#_limitations_of_working_with_tml_files) apply when using the scriptability tool.
    * The author of new content is the user in the config file, not the original author.

    The following are some known issues when using the tool:

    * Worksheets based on SQL Views can sometimes fail.  This is a TML limitation.

    * There are scenarios where there is content you can access, but not download.  In these cases you will get an error message.

    In general, any changes with dependencies are likely to cause errors in the current version.  

??? important "New features being considered for upcoming releases"

    The following features are being considered for an upcoming release:

    * Set the author on import
    * Get only content modified since a given date
    * Automatic versioning of mapping files
    * Ability to compare two environements for differences

    Other ideas are welcome.  Submit a request via [GitHub][gh_issue].


!!! info "Helpful Links"

    :gear: &nbsp; __[Scriptability documentation](https://docs.thoughtspot.com/cloud/latest/scriptability){ target='secondary' .external-link }__

## Detailed scenarios

=== "Exporting TML"

    Some customers want to back up the metadata as TML in the file system or a version control system (VCS), such as `git`.  This is done simply by using the `scriptability --export` and saving the files to a directory.  Then you can use the VCS to add the TML. 

=== "Migrate content"

    Migrating content consist of exporting, (optionally) modifying, and then importing content.  You will want to do the following for this scenario:

    1. Create the connection and tables manually if they don't exist.  This step is needed because the scriptability tool doesn't currently support connections.
    2. Create a mapping file for tables if one doesn't exist.  Note that you can use `scriptability create-mapping` to create a new, empty mapping file.
    3. Export the TML to be migrated using `scriptability export`.
    4. (Optional) Modify the TML as appropriate.  
    5. Import the TML using `scriptability import --force-create`.  The `force-create` parameter will make sure the content is created as new and not updating existing content.

    NOTE: To migrate changes, simply leave out the `--force-create` parameter.  New content will automatically be created and existing content (based on the mapping file) will be updated.

=== "Updating content"

    Updating and reimporting is basically the same steps as migrating new content.  In this step you would:

    1. Export the TML using `scriptability export`.
    2. Modify the TML.
    3. Import the TML using `scriptability import` without the `--force-create` flag.  

=== "Making copies"

    One scenario that comes up is that a ThoughtSpot administrator is managing content for different customers or groups.  They have a set of common content, but want to make copies for each group.  This can be done similarly to the migration of content, though it's usually back to the same instance.

    1. Export the TML using `scriptability export`.
    2. Modify the TML for the group, such as different column names.
    3. Import the TML using `scriptability import` without the `--force-create` flag.

    In this scenario a mapping file _may_ be needed if the content comes from different connections.  In that case you may also want separate mapping files for each group to make a copy for.

    This technique can also be used to localize content.

## GUID mapping file

You will usually need to have an explicit mapping from one GUID to another.  This is particularly true 
of tables if there are more than one with the same name in the system being imported to.  If you don't 
provide the GUID as an FQN in the TML file, you will get an error on import, because ThoughtSpot won't 
know which table is being referred to.

The default name for the GUID mapping file is `guid.mapping.json`, but you can use whatever name you like 
since it's specified as a parameter.  The GUID mapping file is only used for importing TML.  When creating 
content, the GUID mapping file is updated as content is created with new GUID mappings.  
This allows it to be used later for updating content.

The GUID mapping file is created and loaded by the [thoughtspot_tml] project.  More details can be found 
[there](https://github.com/thoughtspot/thoughtspot_tml).  

## CLI preview

=== "scriptability --help"
    ~cs~tools cs_tools tools scriptability --help

=== "scriptability connection-check"
    ~cs~tools cs_tools tools scriptability connection-check --help

=== "scriptability export"
    ~cs~tools cs_tools tools scriptability export --help

=== "scriptability import"
    ~cs~tools cs_tools tools scriptability import --help

=== "scriptability compare"
    ~cs~tools cs_tools tools scriptability compare --help

---

## Changelog

!!! tldr ":octicons-tag-16: v2.0.0 &nbsp; &nbsp; :material-calendar-text: 2023-05-08"
    === ":hammer_and_wrench: &nbsp; Added"
        - Import connections and SQL views
        - Support for Orgs
        - Updated mapping file format
        - Using new version of thoughtspot_tml
        - Multiple bug fixes

??? info "Changes History"

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
