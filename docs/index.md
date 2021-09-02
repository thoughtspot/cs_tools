---
hide:
  - navigation
  - toc
---

<style>
  .md-grid { max-width: 75%; }
  .md-typeset h1,
  .md-content__button { display: none; }
</style>

<figure>
  <img src="assets/logo_black.svg" width="350"/>
  <figcaption>field engineering tooling tuned for customer delight</figcaption>
</figure>

CS Tools is a utility written by the __ThoughtSpot__ Professional Services & Customer
Success teams, used for interacting with your ThoughtSpot platform. It is designed with
a focus on being simple enough for non-technical users to operate.

!!! info "Helpful Links"

    :tools: &nbsp; __[All of our Tools][docs-tools]__

    :smile: &nbsp; __[Installation Guide][docs-install]__

    :gear: &nbsp; __[Setup a configuration file][docs-howto-config]__

---

<center>
__Documentation__: [https://cs_tools.thoughtspot.com/][this]

__Source Code__: [https://github.com/thoughtspot/cs_tools/][gh-main]
</center>

---

## __Getting Started__ for Developers

To work on `cs_tools`, you'll want to have :fontawesome-brands-git-alt:
[git][install-git] and :fontawesome-brands-python: [python 3.6.8][install-python]+
installed on your machine. Then you can [clone the source][gh-clone] from github, and be
up and running in less than 5 minutes!

=== ":fontawesome-brands-apple: Mac"

    ++cmd+space++, &nbsp; type `terminal`, &nbsp; ++enter++
    ```bash
    python3 -m venv $HOME/.cs_tools-dev
    source $HOME/.cs_tools-dev/bin/activate.bat
    pip install -r dev-requirements.txt
    ```

=== ":fontawesome-brands-linux: Linux"

    *if in a GUI environment*, &nbsp; ++ctrl+shift+t++
    ```bash
    python3 -m venv $HOME/.cs_tools-dev
    source $HOME/.cs_tools-dev/bin/activate.bat
    pip install -r dev-requirements.txt
    ```

=== ":fontawesome-brands-windows: Windows"

    ++windows++, &nbsp; type `cmd`, &nbsp; ++enter++
    ```powershell
    python -m venv %USERPROFILE%\.cs_tools-dev
    %USERPROFILE%\.cs_tools-dev\Scripts\activate.bat
    pip install -r dev-requirements.txt
    ```

Should you find anything about the docs or `cs_tools` itself lacking, [please submit an
issue][gh-issue]!

[this]: https://cs_tools.thoughtspot.com/
[docs-tools]: cs-tools/overview.md
[docs-install]: how-to/install-upgrade-cs-tools.md
[docs-howto-config]: how-to/configuration-file.md
[gh-main]: https://github.com/thoughtspot/cs_tools/
[gh-issue]: https://github.com/thoughtspot/cs_tools/issues/new
[gh-clone]: https://docs.github.com/en/github/creating-cloning-and-archiving-repositories/cloning-a-repository-from-github/cloning-a-repository
[install-git]: https://git-scm.com/downloads
[install-python]: https://www.python.org/downloads
