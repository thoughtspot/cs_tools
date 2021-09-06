<style>
  .md-typeset h1, .md-content__button { display: none; }
</style>


## __Getting Started__ for Developers

To work on `cs_tools`, you'll want to have :fontawesome-brands-git-alt:
[git][install-git] and :fontawesome-brands-python: [python 3.6.8][install-python]+
installed on your machine. Then you can [clone the source][gh-clone] from github, and be
up and running in less than 5 minutes!

=== ":fontawesome-brands-apple: Mac"

    ++cmd+space++, &nbsp; type `terminal`, &nbsp; ++enter++
    ```bash
    # change $HOME/cs_tools to where you want to save your local copy of the repository
    git clone https://github.com/thoughtspot/cs_tools.git $HOME/cs_tools
    python3 -m venv $HOME/.cs_tools-dev
    source $HOME/.cs_tools-dev/bin/activate.bat
    pip install -r dev-requirements.txt
    ```

=== ":fontawesome-brands-linux: Linux"

    *if in a GUI environment*, &nbsp; ++ctrl+shift+t++
    ```bash
    # change $HOME/cs_tools to where you want to save your local copy of the repository
    git clone https://github.com/thoughtspot/cs_tools.git $HOME/cs_tools
    python3 -m venv $HOME/.cs_tools-dev
    source $HOME/.cs_tools-dev/bin/activate.bat
    pip install -r dev-requirements.txt
    ```

=== ":fontawesome-brands-windows: Windows"

    ++windows++, &nbsp; type `cmd`, &nbsp; ++enter++
    ```powershell
    # change %USERPROFILE%/cs_tools to where you want to save your local copy of the repository
    git clone https://github.com/thoughtspot/cs_tools.git %USERPROFILE%/cs_tools
    python -m venv %USERPROFILE%\.cs_tools-dev
    %USERPROFILE%\.cs_tools-dev\Scripts\activate.bat
    pip install -r dev-requirements.txt
    ```


## Virtual Environments

While not strictly necessary, a virtual environment is an incredibly useful tool to use
when writing and maintaining several python projects on a single machine.

Each virtual environment has its own Python binary (which matches the version of the
that was used to create that environment) and can have its own *independent* set of
installed Python packages in its site directories.

!!! hint ""

    At its core, the main purpose of Python virtual environments is to create an
    isolated environment for Python projects. This means that each project can have its
    own dependencies, regardless of what dependencies every other project has.

    *For full breakdown, see [Real Python's tutorial][rp-venv] on virtual environments.*


[gh-clone]: https://docs.github.com/en/github/creating-cloning-and-archiving-repositories/cloning-a-repository-from-github/cloning-a-repository
[install-git]: https://git-scm.com/downloads
[install-python]: https://www.python.org/downloads
[rp-venv]: https://realpython.com/python-virtual-environments-a-primer/
