# Installing with a Client

We recognize that not all users of this library are experts with Python, virtualization,
and software development best practices. For this reason, we've added this guide on how
to get up and running with CS Tools on client machines or their ThoughtSpot instances.

TODO:
- investigate github [ssh keys](https://docs.github.com/en/github/authenticating-to-github/generating-a-new-ssh-key-and-adding-it-to-the-ssh-agent) & [anon accounts](https://stackoverflow.com/a/45547413)
- investigate more streamlined approach to running tools
    - NOTE: probably by including pre-built tools as submodule(s), client can then
      install like `pip install cs_tools[depchecker]`

## Client's machine DOES NOT have access to the outside internet

TODO:
- investigate `.whl`
- investigate `pip download -r ... -d ...` and `pip install * f ./ --no-index`
  1. Lorem ipsum..

## Client's machine has access to the outside internet

1. Download and share the current repository [zipfile][master-zip] with the customer.
2. Share the [Best Practices: Virtual Environment][bp-venv] steps with the customer.
    - **the final step** in the above should be replaced with ...
        - `pip install /path/to/cs_tools.zip`
3. Share the subdirectory of the script you choose with the customer.
    - if that means you want to share [Dependency Checker][tool-depchecker], then copy
      that **whole** directory, and then have the client reference it in order to run
      the tool
    - e.g. `"$HOME/Downloads/cs_tools/tools/dependency checker/list_dependents.py"`
    - e.g. `"%USERPROFILE%/Downloads/cs_tools/tools/dependency checker/list_dependents.py"`

[master-zip]: https://github.com/thoughtspot/cs_tools/archive/master.zip
[bp-venv]: https://github.com/thoughtspot/cs_tools/best-practices/virtual-environment.md
[tool-depchecker]: https://github.com/thoughtspot/cs_tools/tree/master/tools/dependency%20checker
