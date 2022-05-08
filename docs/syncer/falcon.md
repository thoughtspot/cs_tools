---
hide:
  - toc
---

??? attention "In Beta"

    The Syncer protocol is in beta, it has been added to __CS Tools__ in v1.3 on a
    __provisional basis__. It may change significantly in future releases and its
    interface will not be concrete until v2.

    Feedback from the community while it's still provisional would be extremely useful;
    either comment on [#25][gh-issue25] or create a new issue.


Falcon is __ThoughtSpot__'s proprietary in-memory database that exists as part of your cluster. Its speed allowed our users to be able to analyze along any dimension without there being any time penalty, giving them a free reign to do any kind of analysis. This data store has been the backbone of many of our long-term customers.

<span class='fc-coral'>__This database is only available for data insertion if you operate on the Software version of the product__</span>, and are not using Embrace Connections to a cloud-native data store.

??? info "Want to see the source code?"
    
    *If you're writing a Custom Syncer, you can check our project code for an example.*

    [cs_tools/sync/__Falcon__/syncer.py][syncer.py]

## Falcon `DEFINITION.toml` spec

> __database__{ .fc-blue }: name of the database to store data within
<br/>*`database` will be created if it does not exist*

> __schema__{ .fc-blue }: <span class=fc-coral>optional</span>, name of the schema to store data within
<br/>*<span class=fc-mint>default</span>:* `falcon_default_schema`
<br/>`schema` *will be created if it does not exist*

> __empty_target__{ .fc-blue }: <span class=fc-coral>optional</span>, either `true` or `false`
<br/>*<span class=fc-mint>default</span>:* `true`
<br/>*a* `TRUNCATE` *statement will be issued prior to loading any data loads if* `true` *is used*


??? question "How do I use the Falcon syncer in commands?"

    === ":fontawesome-brands-apple: Mac, :fontawesome-brands-linux: Linux"

        `cs_tools tools searchable bi-server falcon:///home/user/syncers/falcon-definition.toml --compact`

        `cs_tools tools searchable bi-server falcon://default --compact`

    === ":fontawesome-brands-windows: Windows"

        `cs_tools tools searchable bi-server falcon://C:\Users\%USERNAME%\Downloads\falcon-definition.toml --compact`

        `cs_tools tools searchable bi-server falcon://default --compact`

    *Learn how to register a default for syncers in [How-to: Setup a Configuration File][how-to-config].*


## Full Definition Example

`definition.toml`
```toml
[configuration]
database = 'cs_tools'
schema = 'falcon_default_schema'
empty_target = true
```

[gh-issue25]: https://github.com/thoughtspot/cs_tools/issues/25
[syncer.py]: https://github.com/thoughtspot/cs_tools/blob/master/cs_tools/sync/falcon/syncer.py
[how-to-config]: ../how-to/configuration-file.md
