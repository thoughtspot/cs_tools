# Install Instructions

ThoughtSpot CS Tools are a collection of different tools that assist implementation and
administration, and may contain API calls that we normally wouldn't share with
customers. The tools are all written in Python and require a Python environment in
which to run.

## **Links**

🗃 [`dist.zip`][distzip] (password: `th0ughtSp0t`)

🛠 [tools offered][tools]

---

Human-friendly instructions explanation!
 - Download dist.zip from above
 - Move it to a location on your machine you're happy to leave it at
      (/Downloads is fine!)
 - Unzip the file
     - If you're on Mac, usually double-clicking the file works fine
     - If you're on Windows, right-click and select "Extract All.."
     - If you're on Linux/ThoughtSpot application, see the commands below
 - Move into the /dist directory that was just created
 - Run the appropriate install file!
     - If you're on Mac
         1. hold `control`
         2. click on `unix_install.sh`
         3. hold `option` and select `Copy "unix_install.sh" as Pathname`
         4. open terminal (`command` and `spacebar`, search for terminal)
         5. type `source ` and paste (`command` and `v`) and hit enter!
     - If you're on Windows
         1. hold `shift` and right-click on `windows_install.ps1`
     - If you're on Linux ... see the commands below

You'll know you've made it when the screen looks something like this

```
(.cs_tools) C:\work\thoughtspot\cs_tools>cs_tools

Usage: cs_tools [OPTIONS] COMMAND [ARGS]...

  Welcome to CS Tools!

  These are scripts and utilities used to assist in the development, implementation, and administration of your
  ThoughtSpot platform.

  All tools and this library are provided as-is. While every effort...
```

---

### Windows Install
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


### MacOS / Linux Install
```console
# 1. Download dist.zip
# 2. Open a Terminal and run the following commands

unzip -u $HOME/downloads/dist.zip -d $HOME/downloads
cd $HOME/downloads/dist
source unix_install.sh


# To activate the environment later (for interactive or automation needs)
# the path to unix_activate.sh must be a valid relative or full path!

    source unix_activate.sh
```

[tools]: ../cs_tools/tools
[distzip]: https://thoughtspot.egnyte.com/dl/MyBRZT6leI/dist.zip_
