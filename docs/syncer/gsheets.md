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

With Google Sheets, you can create and edit spreadsheets directly in your web browser - no special software is required. Multiple people can work simultaneously, you can see people’s changes as they make them, and every change is saved automatically.

<span class=fc-coral>__In order to use the Google Sheets syncer__</span>, you must first configure your local environment. The setup instructions below will help you create a __Google Cloud Project__ and utilize the OAuth Client ID workflow to allow __CS Tools__ to selectively interact with your Google Sheet.

??? example "Setup instructions"

    1. Head to [Google Developers Console][gc-dev-console] and create a new project (or select the one you already have).
        - In the box labeled <span class=fc-blue>__Search for APIs and Services__</span>, search for <span class=fc-blue>__Google Drive API__</span> and enable it.
        - In the box labeled <span class=fc-blue>__Search for APIs and Services__</span>, search for <span class=fc-blue>__Google Sheets API__</span> and enable it.
    2. Go to <span class=fc-blue>__APIs & Services > OAuth Consent Screen.__</span> Click the button for <span class=fc-blue>__Configure Consent Screen__</span>
        - In the <span class=fc-blue>__1 OAuth consent screen__</span> tab, give your app a name and fill the <span class=fc-blue>__User support email__</span> and <span class=fc-blue>__Developer contact information__</span>. Click <span class=fc-blue>__SAVE AND CONTINUE__</span>.
        - There is no need to fill in anything in the tab <span class=fc-blue>__2 Scopes__</span>, just click <span class=fc-blue>__SAVE AND CONTINUE__</span>.
        - In the tab <span class=fc-blue>__3 Test users__</span>, add the Google account email of the end user, typically your own Google email. Click <span class=fc-blue>__SAVE AND CONTINUE__</span>.
        - Double check the <span class=fc-blue>__4 Summary__</span> presented and click <span class=fc-blue>__BACK TO DASHBOARD__</span>.
    3. Go to <span class=fc-blue>__APIs & Services > Credentials__</span>
    4. Click <span class=fc-blue>__+ Create credentials__</span> at the top, then select <span class=fc-blue>__OAuth client ID__</span>.
    5. Select <span class=fc-blue>__Desktop app__</span>, name the credentials and click <span class=fc-blue>__Create__</span>. Click <span class=fc-blue>__Ok__</span> in the <span class=fc-blue>__OAuth client created__</span> popup.
    6. Download the credentials by clicking the Download JSON button in <span class=fc-blue>__OAuth 2.0 Client IDs__</span> section.
    
    __[optional]__{ .fc-purple }
    <br/>:fontawesome-brands-apple:, :fontawesome-brands-linux: Move the downloaded file to `~/.config/cs_tools/gsheets/credentials.json`.
    <br/>:fontawesome-brands-windows: Move the downloaded file to `%APPDATA%\cs_tools\gsheets\credentials.json`.


??? info "Want to see the source code?"
    
    *If you're writing a Custom Syncer, you can check our project code for an example.*

    [cs_tools/sync/__gsheets__/syncer.py][syncer.py]

## Google Sheets `DEFINITION.toml` spec

> __spreadsheet__{ .fc-blue }: name of the google sheet to interact with

> __mode__{ .fc-blue }: <span class=fc-coral>optional</span>, either `append` or `overwrite`
<br/>*<span class=fc-mint>default</span>:* `overwrite`

> __credentials_file__{ .fc-blue }: <span class=fc-coral>optional</span>, absolute path to your credentials JSON file
<br/>*<span class=fc-mint>default</span>:* `cs_tools-app-directory/gsheets/credentials.json`
<br/>*you can find the cs_tools app directory by running `cs_tools config show`*


??? question "How do I use the Google Sheets syncer in commands?"

    === ":fontawesome-brands-apple: Mac, :fontawesome-brands-linux: Linux"

        `cs_tools tools searchable bi-server gsheets:///home/user/syncers/google-sheets-definition.toml --compact`

        `cs_tools tools searchable bi-server gsheets://default --compact`

    === ":fontawesome-brands-windows: Windows"

        `cs_tools tools searchable bi-server gsheets://C:\Users\%USERNAME%\Downloads\google-sheets-definition.toml --compact`

        `cs_tools tools searchable bi-server gsheets://default --compact`

    *Learn how to register a default for syncers in [How-to: Setup a Configuration File][how-to-config].*


## Full Definition Example

`definition.toml`
```toml
[configuration]
spreadsheet = 'ThoughtSpot Data Sink'
mode = 'overwrite'
credentials_file = 'C:\Users\NameyNamerson\Downloads\syncers\<project-name>.json'
```

[gh-issue25]: https://github.com/thoughtspot/cs_tools/issues/25
[syncer.py]: https://github.com/thoughtspot/cs_tools/blob/master/cs_tools/sync/gsheets/syncer.py
[gc-dev-console]: https://console.cloud.google.com/apis/dashboard
[how-to-config]: ../tutorial/config.md
