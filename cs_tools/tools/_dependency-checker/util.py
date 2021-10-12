import threading
import queue

from cs_tools.tools import common


class FileQueue:

    def __init__(self, fp):
        self.fp = fp
        self.queue = queue.Queue()
        self.thread = threading.Thread(target=self.save_data)
        self.running = False

    def put(self, data):
        self.queue.put(data)

    def save_data(self):
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

    def start(self):
        self.running = True
        self.thread.start()
        return self

    def stop(self):
        self.running = False
        return self

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *a):
        self.stop()
