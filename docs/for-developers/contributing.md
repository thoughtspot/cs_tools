---
title: Contributing
---

# :tada: &nbsp; Thanks for your interest in cs_tools! &nbsp; :tada:

!!! tip "Everyone Can Participate!"

    We strongly believe everyone in PS/CS can participate, no matter what their
    technical proficiency is. If you don't know where to start, see the Github Issue
    Tracker filtered to [Good First Issue][fi]{ target='secondary' .external-link }.

This project is maintained by the Professional Services and Customer Success
organizations. It is meant to help client manage and scale their ThoughtSpot platform.

CS Tools offers this additional feature set primarily through a command line interface.
Most tools have a python base, with an optional web-based application written primary
in HTML and javascript.

To contribute to the project, you'll want to [setup your development environment][setup]{ .internal-link }.

## Installation

`cs_tools` can be directly used from GitHub by cloning the repository into a directory
on your machine[^1]:

```
git clone https://github.com/thoughtspot/cs_tools.git
```

When cloning from `git`, you must install all required dependencies[^2] yourself:

```
pip install -r cs_tools/dev-requirements.txt
```

### A note on our __Branch Strategy__

- Maintainers merge pull requests
- Maintainers merge back into `master`
- All coordination will happen on `dev`
- New features, documentation or hotfixes require you to branch off `dev`
- All changes must be submitted via Pull Request and go through code review
- include branch_strategy.png

[^1]:
    If you're already lost by the install instructions, you might want to start by
    [setting up your environment][setup]{ .internal-link }!

[^2]: 
    It is highly recommended that you first [set up a virtual environment][venv]{ .internal-link }.

[setup]: ../environment-setup
[venv]: ../environment-setup#virtual-environments
[fi]: https://github.com/thoughtspot/cs_tools/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22
