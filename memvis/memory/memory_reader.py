import logging
import re as regex
from ptrace import debugger
from .stack_pointer_reader import StackPointerReaderError
from .stack_pointer_reader import PtraceStackPointerReader
from .stack_pointer_reader import SyscallFileStackPointerReader


MEMORY_MAP_LINE_REGEX = debugger.memory_mapping.PROC_MAP_REGEX


def get_process_maps_path(process_id):
    return "/proc/" + str(process_id) + "/maps"


def get_process_mem_path(process_id):
    return "/proc/" + str(process_id) + "/mem"


def convert_hex_to_int(hex_string):
    if not hex_string.startswith("0x"):
        hex_string = "0x" + hex_string
    return int(hex_string, 16)


class AddressSpaceMetadata(object):
    def __init__(self, memory_map_line):
        self.log = logging.getLogger(self.__class__.__name__)
        line_groups = self.__match_line(memory_map_line)
        self.address_range = line_groups.group(1), line_groups.group(2)
        self.update_memory_size()
        self.permissions = line_groups.group(3)
        self.offset = convert_hex_to_int(line_groups.group(4))
        self.device = line_groups.group(5) + ":" + line_groups.group(6)
        self.inode = line_groups.group(7)
        self.path_name = line_groups.group(8)

    def is_readable(self):
        return "r" in self.permissions

    def is_writable(self):
        return "w" in self.permissions

    def is_executable(self):
        return "x" in self.permissions

    def is_shared(self):
        return "s" in self.permissions

    def is_private(self):
        return "p" in self.permissions

    def get_address_range_ints(self):
        start, end = self.address_range
        return convert_hex_to_int(start), convert_hex_to_int(end)

    def __match_line(self, memory_map_line):
        matcher = regex.compile(MEMORY_MAP_LINE_REGEX)
        matches = matcher.match(memory_map_line)
        if matches is None:
            message = "Failed to match memory map line : {} with pattern : {}."\
                .format(memory_map_line, MEMORY_MAP_LINE_REGEX)
            self.log.error(message)
            raise ValueError(message)
        return matches

    def update_memory_size(self):
        start_address = convert_hex_to_int(self.address_range[0])
        end_address = convert_hex_to_int(self.address_range[1])
        self.memory_size = end_address - start_address

    def __str__(self):
        return "({}, {}, {}, {}, {}, {}, {})".format(self.address_range[0], self.address_range[1],
                                                     self.permissions, self.offset, self.device, self.inode, self.path_name)

    def __eq__(self, other):
        if not isinstance(other, AddressSpaceMetadata):
            return NotImplemented
        elif self is other:
            return True
        else:
            return self.address_range == other.address_range \
                and self.memory_size == other.memory_size \
                and self.offset == other.offset \
                and self.inode == other.inode \
                and self.path_name == other.path_name \
                and self.permissions == other.permissions


class MemoryMap(object):

    def __init__(self, pid, metadata, memory_bytes):
        self.pid = pid
        self.metadata = metadata
        self.memory_bytes = memory_bytes


class MemoryReaderError(Exception):
    pass


class MemoryReader(object):
    def __init__(self, target_pid, use_ptrace=True):
        self._log = logging.getLogger(self.__class__.__name__)
        self.target_pid = target_pid
        self.refresh_memory_map_metadata()
        if use_ptrace:
            self.stack_pointer_reader = PtraceStackPointerReader()
        else:
            self.stack_pointer_reader = SyscallFileStackPointerReader()

    def read_memory(self):
        memory_maps = []

        for metadata in self.maps_metadata:
            if metadata.is_readable():
                if(metadata.path_name == "[stack]"):
                    _, memory_map = self.__read_stack_address_range(metadata)
                else:
                    raw_data = self.__read_memory_snapshot(metadata)
                    memory_map = MemoryMap(self.target_pid, metadata, raw_data)
                memory_maps.append(memory_map)

        return memory_maps

    def refresh_memory_map_metadata(self):
        self.maps_metadata = self.__read_memory_mappings()

    def get_stack_pointer(self):
        return self.__get_stack_pointer()

    def read_current_call_stack(self):
        metadata = self.__get_stack_metadata()
        return self.__read_stack_address_range(metadata)

    def __read_stack_address_range(self, metadata):
        stack_pointer = self.__get_stack_pointer()
        _, end_address = metadata.address_range
        metadata.address_range = stack_pointer, end_address
        metadata.update_memory_size()

        memory_length = convert_hex_to_int(end_address) -\
            convert_hex_to_int(stack_pointer)
        stack_data = self.__read_stack_data(stack_pointer, memory_length)

        return stack_pointer, MemoryMap(self.target_pid, metadata, stack_data)

    def __get_stack_pointer(self):
        try:
            return self.stack_pointer_reader.read_stack_pointer(
                self.target_pid)
        except StackPointerReaderError as exception:
            message = 'Failed to read stack pointer for process: {}'\
                .format(self.target_pid)
            self._log.error(message, exception)
            raise MemoryReaderError(message) from exception

    def __read_stack_data(self, stack_pointer, memory_size):
        try:
            return self.__read_mems_file(stack_pointer, memory_size)
        except IOError as exception:
            message = 'Failed to read stack with size : {} from mem file at : {}.' + \
                ' Stack pointer position : {}' \
                .format(get_process_mem_path(self.target_pid))
            self._log.error(message, exception)
            raise MemoryReaderError(message) from exception

    def __get_stack_metadata(self):
        for metadata in self.maps_metadata:
            if metadata.path_name == '[stack]':
                return metadata

        raise MemoryError("No stack memory map found.")

    def __read_memory_snapshot(self, metadata):
        try:
            start_address, _ = metadata.address_range
            return self.__read_mems_file(start_address, metadata.memory_size)
        except IOError as error:
            return self.__handle_memory_read_error(error, metadata)
        except OSError as error:
            return self.__handle_memory_read_error(error, metadata)
        except ValueError as error:
            return self.__handle_memory_read_error(error, metadata)

    def __handle_memory_read_error(self, error, metadata):
        message = 'Failed to read memory mapping : {} from mems file at : {}'\
            .format(metadata, get_process_mem_path(self.target_pid))
        self._log.info(message, error)
        return [0] * metadata.memory_size

    def __read_mems_file(self, start_address, memory_size):
        mems_path = get_process_mem_path(self.target_pid)
        with open(mems_path, "rb") as mems_file:
            offset = convert_hex_to_int(start_address)
            mems_file.seek(offset)
            return list(mems_file.read(memory_size))

    def __read_memory_mappings(self):
        memory_space_lines = self.__read_process_maps_file()
        map_metadata = []

        for line in memory_space_lines:
            map_metadata.append(self.__convert_to_metadata(line))

        return map_metadata

    def __convert_to_metadata(self, line):
        try:
            return AddressSpaceMetadata(line)
        except ValueError as exception:
            message = "Failed to create AddressSpaceMetadata"
            self._log.error(message)
            raise MemoryReaderError(message) from exception

    def __read_process_maps_file(self):
        try:
            maps_path = get_process_maps_path(self.target_pid)
            return self.__read_maps_file(maps_path)
        except IOError as exception:
            message = "Failed to read maps file at : {}. Cause : {}"\
                .format(maps_path, str(exception))
            self._log.error(message, exception)
            raise MemoryReaderError(message) from exception

    def __read_maps_file(self, maps_path):
        with open(maps_path) as maps_file:
            return maps_file.readlines()
