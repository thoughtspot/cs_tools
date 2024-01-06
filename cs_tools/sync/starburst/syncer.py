from __future__ import annotations

from cs_tools.sync.trino import Trino


class Starburst(Trino):
    """
    Interact with a Starburst database.

    Starburst is basically Presto (Trino), with a web services layer.
    """

    def __repr__(self):
        return f"<StarburstSyncer conn_string='{self.engine.url}'>"
