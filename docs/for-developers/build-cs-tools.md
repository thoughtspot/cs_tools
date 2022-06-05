
# For development setup and installs, we use `poetry`
  - Dependency management is hard.
  - DM against the below support matrix harder.

# Support Matrix
  - Python Versions: py368, py37, py39, py310, soon: py311
  - Platforms: OSX, Linux, Windows

# Development setup
  - consider pyenv (or pyenv-win)
  - consider installing nox globally
      https://github.com/wntrblm/nox
      https://medium.com/@cjolowicz/nox-is-a-part-of-your-global-developer-environment-like-poetry-pre-commit-pyenv-or-pipx-1cdeba9198bd
      if you want to be really careful,
            python3 -m pip install --user nox
            python -m pip install --user nox

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
