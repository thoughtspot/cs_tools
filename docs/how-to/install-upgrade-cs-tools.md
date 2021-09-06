---
hide:
  - navigation
  - toc
---

<style>
  /* Hide the Edit on Github button */
  .md-typeset h1, .md-content__button { display: none; }
  /* Skinny down and center the page */
  .md-content { max-width: 75%; margin: auto; }
  .md-button { width: 50%; text-align: center; margin: auto; }
  .md-typeset .admonition { margin: 1%; min-width: 48%; min-height: calc(1rem * 5); }
</style>

<center>
## __Getting Started__ with `cs_tools`

To install `cs_tools` on your machine, you'll want to download our pre-built
distribution. This is a compressed directory containing all the files necessary to set
up the environment[^1]. Please click the button below to get the zip file, and then
follow the instructions down the page.
</center>

!!! warning inline "Pre-requisites"
    The only strict requirement for CS Tools to function is 
    [Python][py]{ target='secondary' .external-link } v3.6.8 or newer.

!!! hint inline "Need to update?"

    Our install script is written to allow both first-time installs __and__ upgrades to
    an environment.

<center>
[:material-tools: &nbsp; cs_tools &nbsp;][fs]{ target='secondary' .md-button .md-button--primary }

<sup>__password__: `th0ughtSp0t`</sup>
</center>

---

??? example ":smile: Human-friendly instructions"

    === ":fontawesome-brands-apple: Mac"

        1. Download dist.zip above.
        2. Move it to a permanent location on your machine.
            - `$HOME/Downloads` is fine
        3. Unzip the file by double-clicking `dist.zip`
        4. Move into the newly created /dist directory
        5. Run `unix_install.sh`

            ++ctrl+left-button++ on `unix_install.sh`

            ++option+left-button++ the option `Copy "unix_install.sh" as Pathname`

            open Termanal (++option+spacebar++ , type "terminal" , ++enter++)

            type `source ` and paste the installer path (++command+v++)

            ++enter++

    === ":fontawesome-brands-linux: Linux"


        1. Download dist.zip above.
        2. Move it to a permanent location on your machine.
            - `$HOME/Downloads` is fine
        3. Unzip and install the tools.
        ```console
        unzip -u $HOME/downloads/dist.zip -d $HOME/downloads
        source $HOME/downloads/dist/unix_install.sh
        ```

    === ":fontawesome-brands-windows: Windows"


        1. Download dist.zip above.
        2. Move it to a permanent location on your machine.
            - `%USERPROFILE%/Downloads` is fine
        3. Unzip the file by ++right-button++ clicking `dist.zip` and selecting "Extract All..."
        4. Move into the newly created /dist folder
        5. Run `windows_install.ps1`

            ++shift+right-button++ on `windows_install.ps1`

??? example ":octicons-terminal-24: Terminal-friendly instructions"

    === ":fontawesome-brands-apple: Mac, :fontawesome-brands-linux: Linux"

        ```console
        # 1. Download dist.zip
        # 2. Open a Terminal and run the following commands

        unzip -u $HOME/downloads/dist.zip -d $HOME/downloads
        source $HOME/downloads/dist/unix_install.sh

        # To activate the environment later (for interactive or automation needs)
        # the path to unix_activate.sh must be a valid relative or full path!

            source unix_activate.sh
        ```

    === ":fontawesome-brands-windows: Windows"

        ```console
        # 1. Download dist.zip
        # 2. Unzip dist.zip
        # 3. Navigate to the folder dist/
        # 4. Right-click windows_install.ps1, select "Run with Powershell"

        # To activate the environment later (for interactive or automation needs)
        # the path to windows_activate.ps1 must be a valid relative or full path!
        powershell -file ./windows_activate.ps1

          -or-

        # Right-click windows_activate.ps1, select "Run with Powershell"
        ```

---

<center><b><i>
   You'll know you've made it when the screen looks something like this. 
</i></b></center>

```console
(.cs_tools) C:\work\thoughtspot\cs_tools>cs_tools

Usage: cs_tools [OPTIONS] COMMAND [ARGS]...

  Welcome to CS Tools!

  These are scripts and utilities used to assist in the development, implementation, and
  administration of your ThoughtSpot platform.

  All tools and this library are provided as-is. While every effort has been made to test and certify
  use of these tools in the various supported ThoughtSpot deployments, each environment is different.

  You should ALWAYS take a snapshot before you make any significant changes to your environment!

  For additional help, please reach out to the ThoughtSpot Customer Success team.

  email: ps-na@thoughtspot.com

Options:
  -h, --help  Show this message and exit.

Commands:
  config  Work with dedicated config files.
  logs    Export and view log files.
  tools   Run an installed tool.
```

[^1]: `cs_tools` is a python-based utility, and will set up its own virtual environment.
[py]: https://www.python.org/downloads/
[fs]: https://thoughtspot.egnyte.com/dl/MyBRZT6leI/dist.zip_
