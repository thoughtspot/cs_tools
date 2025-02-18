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
    ~cs~tools tools archiver --help

=== "archiver identify"
    ~cs~tools tools archiver identify --help

=== "archiver untag"
    ~cs~tools tools archiver untag --help

=== "archiver remove"
    ~cs~tools tools archiver remove --help


[contrib-boonhapus]: https://github.com/boonhapus
