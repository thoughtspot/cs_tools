---
icon: material/file
hide:
  - toc
---

??? example "Setup instructions"

    1. Head to [Google Developers Console][gc-dev-console] and create a new project (or select the one you already have).
        - In the box labeled __Search for APIs and Services__{ .fc-purple }, search for __Google Drive API__{ .fc-purple } and enable it.
        - In the box labeled __Search for APIs and Services__{ .fc-purple }, search for __Google Sheets API__{ .fc-purple } and enable it.
    2. Go to __APIs & Services > OAuth Consent Screen.__{ .fc-purple } Click the button for __Configure Consent Screen__{ .fc-purple }
        - In the __1 OAuth consent screen__{ .fc-purple } tab, give your app a name and fill the __User support email__{ .fc-purple } and __Developer contact information__{ .fc-purple }. Click __SAVE AND CONTINUE__{ .fc-purple }.
        - There is no need to fill in anything in the tab __2 Scopes__{ .fc-purple }, just click __SAVE AND CONTINUE__{ .fc-purple }.
        - In the tab __3 Test users__{ .fc-purple }, add the Google account email of the end user, typically your own Google email. Click __SAVE AND CONTINUE__{ .fc-purple }.
        - Double check the __4 Summary__{ .fc-purple } presented and click __BACK TO DASHBOARD__{ .fc-purple }.
    3. Go to __APIs & Services > Credentials__{ .fc-purple }
    4. Click __+ Create credentials__{ .fc-purple } at the top, then select __OAuth client ID__{ .fc-purple }.
    5. Select __Desktop app__{ .fc-purple }, name the credentials and click __Create__{ .fc-purple }. Click __Ok__{ .fc-purple } in the __OAuth client created__{ .fc-purple } popup.
    6. Download the credentials by clicking the Download JSON button in __OAuth 2.0 Client IDs__{ .fc-purple } section.
    7. __Share your Spreadsheet with Editor access__{ .fc-purple } to Service Account that you created.


!!! note "Parameters"

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

    ---

    ??? danger "Serverless Requirements"

        If you're running __CS Tools__ [&nbsp; :simple-serverless: &nbsp;__serverless__][cs-tools-serverless], you'll want to ensure you install these [&nbsp; :simple-python: &nbsp;__python requirements__][syncer-manifest].

        :cstools-mage: __Don't know what this means? It's probably safe to ignore it.__{ .fc-purple }


??? question "How do I use the Syncer in commands?"

    __CS Tools__ accepts syncer definitions in either declarative or configuration file form.

    <sub class=fc-blue>Find the copy button :material-content-copy: to the right of the code block.</sub>

    === ":mega: &nbsp; Declarative"

        Simply write the parameters out alongside the command.

        ```bash
        cs_tools tools searchable metadata --syncer "gsheets://spreadsheet=thoughtspot&credentials_file=/path/to/cs_tools/gsheets/credentials.json" --config dogfood
        ```

        <sup class=fc-gray><i>* when declaring multiple parameters inline, you should <b class=fc-purple>wrap the enter value</b> in quotes.</i></sup>

    === ":recycle: &nbsp; Configuration File"

        1. Create a file with `.toml` extension.

            ??? abstract "syncer-overwrite.toml"
                ```toml
                [configuration]
                spreadsheet = "thoughtspot"
                credentials_keyfile = "/path/to/cs_tools/gsheets/credentials.json"
                date_time_format = "%Y-%m-%dT%H:%M:%S%z"
                save_strategy = "OVERWRITE"
                ```
                <sup class=fc-gray><i>* this is a complete example, not all parameters are <b class=fc-red>required</b>.</i></sup>

        2. Reference the filename in your command in place of the parameters.

            ```bash
            cs_tools tools searchable metadata --syncer gsheets://syncer-overwrite.toml --config dogfood
            ```

[cs-tools-serverless]: ../../getting-started/#__tabbed_1_4
[syncer-manifest]: https://github.com/thoughtspot/cs_tools/blob/master/cs_tools/sync/gsheets/MANIFEST.json
[gc-dev-console]: https://console.cloud.google.com/apis/dashboard
