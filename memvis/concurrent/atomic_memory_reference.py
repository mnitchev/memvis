from threading import Lock
from ..memory.memory_reader import convert_hex_to_int
from ..memory.memory_reader import MemoryReader
import logging


class AddressRange(object):
    def __init__(self, start, end):
        self.start = convert_hex_to_int(start)
        self.end = convert_hex_to_int(end)

    def __eq__(self, other):
        return self.start == other.start and \
            self.end == other.end

    def __lt__(self, other):
        return self.start < other.start

    def __hash__(self):
        return self.start.__hash__()


class AtomicMemoryReference(object):
    def __init__(self):
        self.__lock = Lock()
        self._log = logging.getLogger(self.__class__.__name__)
        self.address_ranges = []
        self.memory_maps = {}

    def get_range(self, startAddress, endAddress):
        result = []
        start = convert_hex_to_int(startAddress)
        end = convert_hex_to_int(endAddress)
        length = end - start
        metadata = None
        for index, address_range in enumerate(self.address_ranges):
            memory_map = self.memory_maps[address_range]
            map_start, map_end = memory_map.metadata.get_address_range_ints()
            if start < map_start:
                slice_end = min(map_start, end)
                zeroes = [0] * (slice_end - start)
                result = result + zeroes
                start = slice_end
            if start > end:
                return index, metadata, result
            if end < map_end:
                slice_start = start - map_start
                slice_end = end - map_start
                memory_slice = memory_map.memory_bytes[slice_start:slice_end]
                result = result + memory_slice
                metadata = memory_map.metadata
                return index, metadata, result
            if end > map_end and start < map_end:
                slice_start = start - map_start
                slice_end = map_end - map_start
                memory_slice = memory_map.memory_bytes[slice_start:slice_end]
                result = result + memory_slice
                start = map_end
                metadata = memory_map.metadata
        if len(result) < length:
            self._log.error(result)
            result = result + [0] * (length - len(result))

        return 0, metadata, result

    def set_memory_maps(self, memory_maps):
        self.memory_maps = {}
        for memory_map in memory_maps:
            start, end = memory_map.metadata.address_range
            address_range = AddressRange(start, end)
            self.memory_maps[address_range] = memory_map

        self.address_ranges = sorted(self.memory_maps)
