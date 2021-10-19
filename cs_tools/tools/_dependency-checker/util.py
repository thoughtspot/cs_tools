from typing import Any, Dict

import threading
import pathlib
import queue

from cs_tools.tools import common


class FileQueue:
    """
    Utility class which bounds memory usage.

    Problem: we are expecting some data from an API call that could
    potentially grow to be larger than the available memory on the
    current machine.

    Solution: Queues! Just consume the already-seen data and write it to
    file periodically. That's the end goal anyway.

    Attributes
    ----------
    fp : pathlib.Path
    """
    def __init__(self, fp: pathlib.Path):
        self.fp = pathlib.Path(fp)
        self.queue = queue.Queue()
        self.thread = threading.Thread(target=self.save_data)
        self.running = False

    def put(self, data: Dict[str, Any]) -> None:
        """
        Write data to the internal queue.
        """
        self.queue.put(data)

    def save_data(self) -> None:
        """
        Consume data from the internal queue.

        This will empty the queue and write that data to file.
        """
        data = []

        while self.running or not self.queue.empty():
            try:
                item = self.queue.get(timeout=2)
                data.append(item)

            except queue.Empty:
                if not data:
                    continue

                common.to_csv(data, self.fp, mode='a')
                data = []

    def start(self) -> None:
        """
        Start the file queue.
        """
        self.running = True
        self.thread.start()
        return self

    def stop(self) -> 'FileQueue':
        """
        Stop the file queue.
        """
        self.running = False
        return self

    def __enter__(self) -> 'FileQueue':
        self.start()
        return self

    def __exit__(self, *a) -> None:
        self.stop()
