def _get_version() -> str:
    """
    Retrieve the version string.
    """
    import pathlib
    import toml

    package_dir = pathlib.Path(__file__).parent.parent
    pyproject_toml = toml.load(package_dir / "pyproject.toml")
    return pyproject_toml["tool"]["poetry"]["version"]


__version__ = _get_version()
