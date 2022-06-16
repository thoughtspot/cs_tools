"""Contains useful classes and methods for scriptability."""
import pathlib

from thoughtspot_tml.tml import TML


class TMLFileBundle:
    """
    Bundles file information with TML to make it easier to track and log.
    """

    def __init__(self, file: pathlib.Path, tml: TML):
        """
        Creates a new TMLFileBundle
        :param file: A path to the TML file.
        :param tml: The TML from the file.  This may be modified.
        """
        self.file = file
        self.tml = tml
