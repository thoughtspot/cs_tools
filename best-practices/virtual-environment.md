# Virtual Environments

**Thank you for contributing to CS Tools!**

The purpose of this document is to help get newer developers get up and runnnig with a
clean python virtual environment.

## What is a Virtual Environment?

At its core, the main purpose of Python virtual environments is to create an isolated
environment for Python projects. This means that each project can have its own
dependencies, regardless of what dependencies every other project has.

The great thing about this is that there are no limits to the number of environments you
can have since they're just directories containing a few scripts. Plus, they're easily
created using many command line tools.

## Using Classic Virtual Environments

### OSX / Linx
```console
mkdir -p %HOME%/.venv
python3 -m venv %HOME%/.venv/cs_tools
source %HOME%/.venv/cs_tools/bin/activate
pip install git+https://github.com/thoughtspot/cs_tools.git
```

### Windows
```console
IF NOT EXIST %USERPROFILE%/.venv MKDIR %USERPROFILE%/.venv
python -m venv %USERPROFILE%/.venv/cs_tools
CALL %USERPROFILE%/.venv/cs_tools/scripts/activate.bat
pip install git+https://github.com/thoughtspot/cs_tools.git
```

Now we are inside our python virtual environment and can install packages at freely,
not needing to care if our actions will have an effect on our other projects. Leaving
the virtual environment is as simple as typing `deactivate`. Whenever we want to
activate the environment again, we simply need to run the final `source` command above.

For a more in-depth look at native support for virtual environments, happy yourself to
reference [Real Python's primer guide][real-python-venv].

## Poetry: Dependency Management for Python

Poetry is another tool useful in creating and managing Python virtual environments. This
is one of the tasks Poetry sets out to resolve, among others. Specifically, Poetry
describes itself as 

> ... a tool for dependency management and packaging in Python. It allows you to declare
the libraries your project depends on and it will manage (install/update) them for you.

In order to do this effectivley, Poetry provides a custom installer, outside of the
Python runtime environment. Let's see how to [get started with Poetry][poetry-install].

### OSX / Linux
```
curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/get-poetry.py | python
```

### Windows Powershell
```
(Invoke-WebRequest -Uri https://raw.githubusercontent.com/python-poetry/poetry/master/get-poetry.py -UseBasicParsing).Content | python
```

From here, to get to a similar setup as above, it's as simple as ...
```console
cd /path/to/some/directory
poetry add git+https://github.com/thoughtspot/cs_tools.git
poetry install
```

Poetry has a number advantages over `pip`.

1. Records all the top-level dependencies
2. Records production & development dependencies separately
3. Allows the user to switch between Python interpreter versions
3. Allows for directly publishing your package to PyPI

Further reading on Poetry can be found at their [documentation page][poetry-usage].

[poetry-install]: https://python-poetry.org/docs/#installation
[real-python-venv]: https://realpython.com/python-virtual-environments-a-primer/
[poetry-usage]: https://python-poetry.org/docs/basic-usage/
