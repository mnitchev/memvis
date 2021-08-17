import logging
import re as regex
from ptrace.debugger import PtraceProcess


HEX_NUMBER_REGEX = "0x[0-9a-f]+"


def get_process_syscall_path(process_id):
    return "/proc/" + str(process_id) + "/syscall"


class StackPointerReaderError(Exception):
    pass


class DummyDebugger(object):
    def deleteProcess(self, process=None, pid=None):
        pass


class PtraceStackPointerReader(object):
    def read_stack_pointer(self, pid):
        process = PtraceProcess(
            debugger=DummyDebugger(), pid=pid, is_attached=False)
        stack_pointer = hex(process.getStackPointer())
        process.was_attached = True
        process.detach()
        return stack_pointer


class SyscallFileStackPointerReader(object):
    def __init__(self):
        self.log = logging.getLogger(self.__class__.__name__)

    def read_stack_pointer(self, pid):
        syscall_line = self.__read_syscall_file(pid)
        matches = regex.findall(HEX_NUMBER_REGEX, syscall_line)
        stack_pointer = matches[len(matches) - 2]

        return stack_pointer

    def __read_syscall_file(self, pid):
        syscall_file_path = get_process_syscall_path(pid)
        try:
            with open(syscall_file_path) as syscall_file:
                syscall_line = syscall_file.readline()

            return syscall_line
        except IOError as exception:
            message = 'Failed to read stack pointer from syscall file at : {}'\
                .format(syscall_file_path)
            self.log.error(message)
            raise StackPointerReaderError(message) from exception
