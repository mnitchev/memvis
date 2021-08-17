import threading
from .cli import Console
from .concurrent import AtomicMemoryReference
from .concurrent import MemoryUpdater


class MemvisController(object):
    def __init__(self, pid, width=26, height=10, start_address=None, use_ptrace=True, convert_ascii=True):
        self.pid = pid
        self.memory_reference = AtomicMemoryReference()
        self.memory_updater = MemoryUpdater(
            pid, self.memory_reference, use_ptrace)
        self.start_address = start_address
        if start_address is None:
            self.start_address = self.memory_updater.get_stack_pointer()
        self.console = Console(
            pid, self.start_address, self.memory_reference, page_height=height, page_width=width,
            convert_ascii=convert_ascii)

    def start(self):
        self.memory_updater.start()
        self.console.start()
        self.memory_updater.stop()
