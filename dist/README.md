# Install Instructions

ThoughtSpot CS Tools are a collection of different tools that assist implementation and
administration, and may contain API calls that we normally wouldn't share with
customers. The tools are all written in Python and require a Python environment in
which to run.

## **Links**

🗃 [`dist.zip`][distzip] (password: `th0ughtSp0t`)

🛠 [tools offered][tools]

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
# 2. Run the following commands

unzip $HOME/downloads/dist.zip
cd $HOME/downloads/dist
source unix_install.sh


# To activate the environment later (for interactive or automation needs)
# the path to unix_activate.sh must be a valid relative or full path!

    source unix_activate.sh
```

[tools]: ../cs_tools/tools
[distzip]: https://thoughtspot.egnyte.com/dl/MyBRZT6leI/dist.zip_
