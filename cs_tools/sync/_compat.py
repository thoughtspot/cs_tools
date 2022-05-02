from typing import Union

try:
    # provisional in py38, accepted in py310
    from importlib.metadata import version
except ImportError:
    from pkg_resources import DistributionNotFound, get_distribution

    def version(package_name: str) -> Union[str, None]:
        """
        Shim for older python versions.

        If a package was installed setup.py, the distribution should have a
        version attribute we can read from.

        Parameters
        ----------
        package_name: str
          name of the package installed

        Returns
        -------
        __version__: str | None
          version of the package installed
        """
        try:
            __version__ = get_distribution(package_name).version
        except DistributionNotFound:
            __version__ = None

        return __version__
