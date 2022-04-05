---
hide:
  - navigation
  - toc
---

<style>
  /* Hide the Header, "Edit on Github" button, and paragraph header link */
  .md-typeset h1, .md-content__button { display: none; }
  .md-typeset .headerlink { display: none; }
  /* Skinny down and center the page */
  .md-content { max-width: 75%; margin: auto; }
  .md-button { width: 50%; text-align: center; margin: auto; }
  .md-typeset .admonition { margin: 1%; min-width: 45%; min-height: calc(1rem * 6); }
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
[:material-tools: &nbsp; get the tools &nbsp;][gf]{ target='secondary' .md-button .md-button--primary }
</center>

---

??? example ":smile: Human-friendly instructions"

    === ":fontawesome-brands-apple: Mac"

        1. Download cs_tools-platform-installer.zip above.
        2. Move it to a permanent location on your machine.
            - `$HOME/Downloads` is fine
        3. Unzip the file by double-clicking `cs_tools-platform-installer.zip`
        4. Move into the newly created /cs_tools-platform-installer directory
        5. Run `unix_install.sh`

            ++ctrl+left-button++ on `unix_install.sh`

            ++option+left-button++ the option `Copy "unix_install.sh" as Pathname`

            open Termanal (++option+spacebar++ , type "terminal" , ++enter++)

            type `source ` and paste the installer path (++command+v++)

            ++enter++

    === ":fontawesome-brands-linux: Linux"


        1. Download cs_tools-platform-installer.zip above.
        2. Move it to a permanent location on your machine.
            - `$HOME/Downloads` is fine
        3. Unzip and install the tools.
        ```console
        unzip -u $HOME/downloads/cs_tools-platform-installer.zip -d $HOME/downloads
        source $HOME/downloads/cs_tools-platform-installer/unix_install.sh
        ```

    === ":fontawesome-brands-windows: Windows"


        1. Download cs_tools-platform-installer.zip above.
        2. Move it to a permanent location on your machine.
            - `%USERPROFILE%/Downloads` is fine
        3. Unzip the file by ++right-button++ clicking `cs_tools-platform-installer.zip` and selecting "Extract All..."
        4. Move into the newly created /cs_tools-platform-installer folder
        5. Run `windows_install.ps1`

            ++shift+right-button++ on `windows_install.ps1`

??? example ":octicons-terminal-24: Terminal-friendly instructions"

    === ":fontawesome-brands-apple: Mac, :fontawesome-brands-linux: Linux"

        ```console
        # 1. Download cs_tools-platform-installer.zip
        # 2. Open a Terminal and run the following commands

        unzip -u $HOME/downloads/cs_tools-platform-installer.zip -d $HOME/downloads
        source $HOME/downloads/cs_tools-platform-installer/unix_install.sh

        # To activate the environment later (for interactive or automation needs)
        # the path to unix_activate.sh must be a valid relative or full path!

            source unix_activate.sh
        ```

    === ":fontawesome-brands-windows: Windows"

        ```console
        # 1. Download cs_tools-platform-installer.zip
        # 2. Unzip cs_tools-platform-installer.zip
        # 3. Navigate to the folder cs_tools-platform-installer/
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
(.cs_tools) C:\work\thoughtspot>cs_tools
Usage: cs_tools [--version, --help] <command>

  Welcome to CS Tools!

  These are scripts and utilities used to assist in the development, implementation, and administration of your ThoughtSpot platform.

  All tools are provided as-is. While every effort has been made to test and certify use of these tools in the various supported
  ThoughtSpot deployments, each environment is different!

  You should ALWAYS take a snapshot before you make any significant changes to your environment!

  For additional help, please visit our documentation!
  https://thoughtspot.github.io/cs_tools/

Options:
  --version               Show the version and exit.
  -h, --help, --helpfull  Show this message and exit.

Commands:
  config  Work with dedicated config files.
  logs    Export and view log files.
  tools   Run an installed tool.
```

[^1]: `cs_tools` is a python-based utility, and will set up its own virtual environment.
[py]: https://www.python.org/downloads/
[fs]: https://thoughtspot.egnyte.com/dl/MyBRZT6leI/dist.zip_
[gf]: https://forms.gle/fNQpF3ubkjQySGo66
