---
hide:
  - toc
---

??? example "In Beta"

    The Syncer protocol is in beta, it has been added to __CS Tools__ in v1.3 on a
    __provisional basis__. It may change significantly in future releases and its
    interface will not be concrete until v2.

    Feedback from the community while it's still provisional would be extremely useful;
    either comment on [#25][gh-issue25] or create a new issue.

__Snowflake__ is a fully managed SaaS (software as a service) that provides a single platform for data warehousing, data lakes, data engineering, data science, data application development, and secure sharing and consumption of real-time / shared data.

__Snowflake__ features out-of-the-box features like separation of storage and compute, on-the-fly scalable compute, data sharing, data cloning, and third-party tools support in order to handle the demanding needs of growing enterprises.


??? info "Want to see the source code?"
    
    *If you're writing a Custom Syncer, you can check our project code for an example.*

    [cs_tools/sync/__snowflake__/syncer.py][syncer.py]


## Snowflake `DEFINITION.toml` spec

> __snowflake_account_identifier__{ .fc-blue }: your snowflake account name
<br/>*your account identifier can be seen in the web interface URL `<account_identifier>.snowflakecomputing.com`*

> __username__{ .fc-blue }: username to your Snowflake account

> __password__{ .fc-blue }: password to your Snowflake account

> __warehouse__{ .fc-blue }: warehouse name for the Snowflake session

> __role__{ .fc-blue }: role name for the Snowflake session

> __database__{ .fc-blue }: database name for the Snowflake session

> __schema\___{ .fc-blue }: <span class=fc-coral>optional</span>, schema name for the Snowflake session
<br/>*<span class=fc-mint>default</span>:* `PUBLIC`

> __auth_type__{ .fc-blue }: <span class=fc-coral>optional</span>, either `local` or `multi-factor`
<br/>*<span class=fc-mint>default</span>:* `local`
<br/>*both local and multi-factor auth use your username and password, <span class=fc-coral>^^if using multi-factor^^ access to a browser window is required*</span>[^1]

> __truncate_on_load__{ .fc-blue }: <span class=fc-coral>optional</span>, either `true` or `false`, remove all data in the table prior to a new data load
<br/>*<span class=fc-mint>default</span>:* `true`


??? question "How do I use the Snowflake syncer in commands?"

    === ":fontawesome-brands-apple: Mac, :fontawesome-brands-linux: Linux"

        `cs_tools tools searchable bi-server snowflake:///home/user/syncers/snowflake-definition.toml --compact`

        `cs_tools tools searchable bi-server snowflake://default --compact`

    === ":fontawesome-brands-windows: Windows"

        `cs_tools tools searchable bi-server snowflake://C:\Users\%USERNAME%\Downloads\snowflake-definition.toml --compact`

        `cs_tools tools searchable bi-server snowflake://default --compact`

    *Learn how to register a default for syncers in [How-to: Setup a Configuration File][how-to-config].*


## Full Definition Example

`definition.toml`
```toml
[configuration]
snowflake_account_identifier = 'thoughtspot'
username = 'namey.namerson@thoughtspot.com'
password = 'Really-Hard-Passphrase-to-Crack'
warehouse = 'DATALOAD_WH_XS'
role = 'SYSADMIN'
database = 'CS_TOOLS'
schema_ = 'PUBLIC'
auth_type = 'multi-factor'
truncate_on_load = true
```

[^1]: 
    While Snowflake supports two methods of multi-factor authentication, CS Tools will utilize [Browser-based SSO][browser-sso]. With browser-based SSO, the Snowflake-provided client (for example, the Snowflake JDBC driver) needs to be able to open the user’s web browser. <span class=fc-coral>__Browser-based SSO does not work if the Snowflake-provided client is used by code that runs on a server.__</span>
    

[gh-issue25]: https://github.com/thoughtspot/cs_tools/issues/25
[syncer.py]: https://github.com/thoughtspot/cs_tools/blob/master/cs_tools/sync/snowflake/syncer.py
[browser-sso]: https://docs.snowflake.com/en/user-guide/admin-security-fed-auth-use.html#browser-based-sso
[how-to-config]: ../tutorial/config.md
