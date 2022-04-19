---
hide:
  - toc
---

Falcon is ThoughtSpot's proprietary in-memory database that exists as part of your
cluster. Its speed allowed our users to be able to analyze along any dimension without
there being any time penalty, giving them a free reign to do any kind of analysis. This
data store has been the backbone of many of our long-term customers.

<span class='fc-coral'>__This database is only available for data insertion if you
operate on the Software version of the product__</span>, and are not using Embrace
Connections to a cloud-native data store.

??? info "Want to see the source code?"
    
    *If you're writing a Custom Syncer, you can check our project code for an example.*

    [cs_tools/sync/__Falcon__/syncer.py][syncer.py]

## Falcon `DEFINITION.toml` spec

> __database__{ .fc-blue }: name of the database to store data within
<br/>*creating it if it doesn't yet exist*

> __schema__{ .fc-blue }: name of the schema to store data within
<br/>*creating it if it doesn't yet exist*

> __empty_target__{ .fc-blue }: either `True` or `False`
<br/>*if `True`, then a `TRUNCATE` statement will be issued prior to loading any data,
on every data load*

## Full Example

`definition.toml`
```toml
[configuration]
database = 'cs_tools'
schema = 'falcon_default_schema'
empty_target = True
```

[syncer.py]: https://github.com/thoughtspot/cs_tools/blob/master/cs_tools/sync/falcon/syncer.py
