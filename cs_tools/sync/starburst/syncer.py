from __future__ import annotations

from cs_tools.sync.trino import Trino


class Starburst(Trino):
    """
    Interact with a Starburst database.

    Starburst is basically Presto (Trino), with a web services layer.
    """

    __syncer_name__ = "starburst"

    def __repr__(self):
        return f"<StarburstSyncer to {self.host}/{self.catalog}>"
