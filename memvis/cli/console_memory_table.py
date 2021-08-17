from prettytable import PrettyTable

ADDRESS = 0
PERMISSIONS = 1
OFFSET = 2
DEVICE = 3
INODE = 4
PATHNAME = 5
MAX_METADATA_LINE = 19
WILDCARD = "????????"


class ConsoleMemoryTable(object):
    def __init__(self, start_address, height=26, width=10, convert_ascii=True):
        self.height = height
        self.width = width
        self.start = 0
        self.end = height * width
        self.start_address = start_address
        self.end_address = self.__calculate_offset_address(
            start_address, self.end)
        self.header = self.__get_header_row()
        self.convert_ascii = convert_ascii
        self.memory_bytes = None

    def set_memory_bytes(self, start_address, metadata, memory_bytes):
        self.start_address = start_address
        self.metadata = metadata
        self.end_address = self.__calculate_offset_address(
            start_address, self.end)
        self.memory_bytes = memory_bytes

    def draw(self):
        start_address_value = int(self.start_address, 16)
        table = PrettyTable(self.header)
        offset = 0
        path_leftover = ""
        for position in range(self.start, self.end, self.width):
            next_line = self.memory_bytes[position: position + self.width]
            line_as_string = []
            metadata_string = self.__get_metadata_at_position(offset)
            if metadata_string == "":
                metadata_string = path_leftover
                path_leftover = ""
            if len(metadata_string) > MAX_METADATA_LINE:
                path_leftover = metadata_string[MAX_METADATA_LINE:]
                metadata_string = metadata_string[:MAX_METADATA_LINE]

            line_as_string += [metadata_string]
            line_as_string = line_as_string + \
                [hex(start_address_value + offset * self.width)]
            line_as_string += list(
                map(lambda x: str(self.__convert_to_ascii_symbol(x)), next_line))
            table.add_row(line_as_string)
            offset += 1

        return str(table)

    def __get_metadata_at_position(self, position):
        if self.metadata is None:
            return WILDCARD
        metadata = {
            0: "Addresses:  ",
            1:  self.__get_address_range(),
            2: "Permissions: " + self.metadata.permissions,
            4: "Offset: " + str(self.metadata.offset),
            6: "Device: " + self.metadata.device,
            8: "Inode: " + str(self.metadata.inode),
            10: "Pathname: " + self.__get_pathname()
        }.get(position)

        if metadata is None:
            return ""
        return metadata

    def __get_address_range(self):
        start, end = self.metadata.address_range
        return start + "-" + end

    def __get_pathname(self):
        path_name = self.metadata.path_name
        if path_name is "":
            return WILDCARD
        return path_name

    def __get_header_row(self):
        header = ["Address Space Data ", "    Address     "]
        for i in range(self.width):
            header = header + [hex(i)]
        return header

    def __calculate_offset_address(self, hex_address, offset):
        address_int = int(hex_address, 16)
        address_int += offset
        return hex(address_int)

    def __convert_to_ascii_symbol(self, byte_value):
        if self.convert_ascii and 31 < byte_value < 127:
            return chr(byte_value)
        hex_value = hex(byte_value)
        if byte_value == 0:
            hex_value += '0'
        return hex_value
