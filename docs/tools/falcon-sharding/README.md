---
hide:
    - toc
---

# Falcon Sharding

This solution allows you to extract key data about Falcon tables to help guide on the
optimal number of shards for each table. Ideally, once implemented, you will run it on a
regular basis, with a plan to review the liveboard once every few months (depending on 
data volume growth).

__Currently, this solution does not consider co-sharding as part of the output.__{ .fc-coral }

If you are not comfortable with the sharding, or want to learn more about what benefit
sharding brings you, please reach out to your __Solutions Consultant__ and we'll
help guide you through the process.

## Liveboard preview

![liveboard](./liveboard.png)

## CLI preview

=== "falcon-sharding --help"
    ~cs~tools tools falcon-sharding --help

=== "sharding-recommender gather"
    ~cs~tools tools falcon-sharding gather --help

=== "sharding-recommender deploy"
    ~cs~tools tools falcon-sharding deploy --help

[contrib-boonhapus]: https://github.com/boonhapus
