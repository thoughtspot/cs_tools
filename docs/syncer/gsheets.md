---
icon: material/file
hide:
  - toc
---

Google Sheets is a free online spreadsheet program that's part of the Google Workspace suite of tools. It's kind of like a digital version of those old-school paper spreadsheets, but way more powerful and flexible.

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

!!! note "Google Sheets parameters"

    ### __Required__ parameters are in __red__{ .fc-red } and __Optional__ parameters are in __blue__{ .fc-blue }.
    
    ---

    - [x] __spreadsheet__{ .fc-red }, _the name of the Google Sheet to write data to_

    ---

    - [x] __credentials_file__{ .fc-red }, _the full path where your credentials.json is located_

    ---

    - [ ] __date_time_format__{ .fc-blue }, _the string representation of date times_
    <br />__default__{ .fc-gray }: `%Y-%m-%dT%H:%M:%S.%f` ( use the [strftime.org](https://strftime.org) cheatsheet as a guide )
    
    ---

    - [ ] __save_strategy__{ .fc-blue }, _how to save new data into an existing directory_
    <br />__default__{ .fc-gray }: `OVERWRITE` ( __allowed__{ .fc-green }: `APPEND`, `OVERWRITE` )


??? question "How do I use the Google Sheets syncer in commands?"

    `cs_tools tools searchable bi-server --syncer gsheets://spreadsheet=data&credentials_file=data-6538a3a8f574.json&save_strategy=APPEND`

    __- or -__{ .fc-blue }

    `cs_tools tools searchable bi-server --syncer gsheets://definition.toml`


## Definition TOML Example

`definition.toml`
```toml
[configuration]
spreadsheet = data
credentials_file = data-6538a3a8f574.json
save_strategy = APPEND
```

[gc-dev-console]: https://console.cloud.google.com/apis/dashboard
