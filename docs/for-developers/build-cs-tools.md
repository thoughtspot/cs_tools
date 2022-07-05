
# For development setup and installs, we use `poetry`
  - Dependency management is hard.
  - DM against the below support matrix harder.

# Support Matrix
  - Python Versions: py368, py37, py39, py310, soon: py311
  - Platforms: OSX, Linux, Windows

# Development setup

  - consider pyenv (or pyenv-win)
      - what is pyenv? it's a way to manage multiple python versions on your local machine
      - this does not replace virtual environments!
      - think of this as a way to have multiple global python environments on the same box
      - priority order:  SHELL --> LOCAL --> GLOBAL --> SYSTEM
      - useful commands
          pyenv versions  :: show all installed versions & active version
          pyenv shell     :: set your python version for this shell session
          pyenv local     :: set your default python version for this directory
          pyenv global    :: set your default python version across the system

  - consider poetry
      - what is poetry? it's a way to manage dependencies for python projects, dependency resolution is HARD
      - py37+ as of poetry==1.2.0
      - useful commands
          peotry add      :: add a package to your dependencies, --dev for dev dependencies
          peotry install  :: read, resolve, and install dependencies, generate a lockfile after resolution
          poetry update   :: get the latest versions of the dependencies and to update the lockfile
          poetry shell    :: spawn a shell, if a virtual env doesn't exist, create one from your current python version
          poetry build    :: --format wheel, build a distributable .whl file

  - consider global packages
      - nox       <--- automation across multiple python versions
      - flake8    <--- linting
      - mypy      <--- static type-checking
      - black     <--- code formatting

  https://medium.com/@cjolowicz/nox-is-a-part-of-your-global-developer-environment-like-poetry-pre-commit-pyenv-or-pipx-1cdeba9198bd


# Install
  - get poetry | python -
  - poetry install
  - poetry show

# Adding / Updating a dependency
  - poetry add --dry-run DEPENDENCY
  - poetry update --dry-run

  // alternate useful versions
  - poetry add --dry-run --dev DEPENDENCY
  - poetry add https://github.com/thoughtspot/cs_tools.git
  - poetry add https://github.com/thoughtspot/cs_tools.git#v1.3.2
  - poetry add https://github.com/thoughtspot/cs_tools.git#my-release-branch

# Deploy a release
  - poetry check
  - poetry run code-quality
    - isort, black, nox, ward, coverage
  - poetry run build
    - https://python-poetry.org/docs/cli/#version
    - https://github.com/python-poetry/poetry/issues/273#issuecomment-767221679
    - https://github.com/python-poetry/poetry/issues/273#issuecomment-1103812336
    - poetry build --format wheel
    - poetry export -f requirements.txt --output requirements.txt
    - check if client requirementstxt output has changed
    - need to add cs_tools to the client-install lockfile

  // hmm...
  https://python-poetry.org/docs/dependency-specification/#git-dependencies
  https://github.com/python-poetry/poetry/issues/558#issuecomment-481064864
  https://github.com/python-poetry/poetry/issues/76#issuecomment-385439995
  - poetry install --no-dev --no-root

  - remote: https://github.com/python-poetry/poetry/blob/master/install-poetry.py | python -
  -  local: python install-poetry.py --path ...

    --path  Install from a given path (file or directory) instead of fetching the latest version of Poetry available online.
    can vendor the latest releases: https://github.com/python-poetry/poetry/releases/tag/1.1.13

# CI / CD
  - https://github.com/python-poetry/poetry/blob/master/.github/workflows/main.yml

# Plugins eventually ?
  - https://www.youtube.com/watch?v=fY3Y_xPKWNA
