import threading
import time
import logging
from ..memory import MemoryReader


class MemoryUpdater(object):
    def __init__(self, pid, memory_reference, use_ptrace=True, update_period=5):
        self._log = logging.getLogger(self.__class__.__name__)
        self.pid = pid
        self.running = False
        self.thread = threading.Thread(target=self.__update_memory_maps)
        self.memory_reference = memory_reference
        self.memory_reader = MemoryReader(pid)
        self.update_period = update_period
        self.exit = threading.Event()

    def start(self):
        self._log.info("Starting memory updater.")
        self.running = True
        self.thread.start()

    def stop(self):
        self.running = False
        self.exit.set()

    def get_stack_pointer(self):
        return self.memory_reader.get_stack_pointer()

    def __del__(self):
        self._log.info("Destroying memory updater.")
        self.running = False
        if self.thread.is_alive():
            self.thread.join()

    def __update_memory_maps(self):
        self._log.info("Updating memory maps.")
        while self.running:
            memory_map = self.memory_reader.read_memory()
            self._log.info("Memory maps size: " + str(len(memory_map)))
            self.memory_reference.set_memory_maps(memory_map)
            self.exit.wait(self.update_period)
