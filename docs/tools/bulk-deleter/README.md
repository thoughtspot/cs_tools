---
hide:
    - toc
---

# Bulk Deleter

Over the life of a ThoughtSpot cluster objects in the system grow. With changes in
employee roles and business problems you may find that tens of thousands of objects can
be left behind. This tool allows you to remove objects from the metadata enmasse. 

The tool separates deletes objects in batches that can be specified in the args to speed
up the delete process, but gives less visibility should an issue occur. A summary of
what has been removed is saved in the logs directory of cs-tools. 

=== "bulk-deleter --help"
    ~cs~tools tools bulk-deleter --help

=== "bulk-deleter from-tabular"
    ~cs~tools tools bulk-deleter from-tabular --help


[contrib-boonhapus]: https://github.com/boonhapus
[contrib-dpm]: https://github.com/DevinMcPherson-TS
