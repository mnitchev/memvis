import unittest
import logging
from memvis import memory_reader as mr
from unittest.mock import patch, call, MagicMock
from ptrace.debugger.process import ProcessError
from memvis.stack_pointer_reader import StackPointerReaderError


class TestUtilities(unittest.TestCase):

    def test_get_process_maps_path(self):
        target_pid = 2222
        expected_path = "/proc/" + str(target_pid) + "/maps"
        actual_path = mr.get_process_maps_path(target_pid)

        self.assertEqual(actual_path, expected_path)

    def test_get_process_mem_path(self):
        target_pid = 2222
        expected_path = "/proc/" + str(target_pid) + "/mem"
        actual_path = mr.get_process_mem_path(target_pid)

        self.assertEqual(actual_path, expected_path)

    def test_convert_hex_to_int(self):
        hex_number = "0x1daa2345f000"
        expected_number = int(hex_number, 16)

        self.__assert_hex_converted(hex_number, expected_number)

    def test_convert_hex_to_int_without_0x(self):
        hex_number = "1daa2345f000"
        expected_number = int("0x" + hex_number, 16)

        self.__assert_hex_converted(hex_number, expected_number)

    def __assert_hex_converted(self, hex_number, expected_number):
        actual_number = mr.convert_hex_to_int(hex_number)
        self.assertEqual(actual_number, expected_number)


class TestAddressSpaceMetadata(unittest.TestCase):

    def __init__(self, *args, **kwargs):
        super(TestAddressSpaceMetadata, self).__init__(*args, **kwargs)
        logging.disable(logging.CRITICAL)

    def test_add_address_space_successful(self):
        address_range = "fff0137c000", "7fff0139d000"
        memory_size = self.__get_memory_size(address_range)
        permissions = "rw-p"
        offset = "00025000"
        device = "00:00"
        inode = "654180"
        path_name = "[stack]"

        address_range_string = "-".join([address_range[0], address_range[1]])
        memory_map_line = " ".join([address_range_string, permissions,
                                    offset, device, inode, path_name])
        metadata = mr.AddressSpaceMetadata(memory_map_line)

        self.assertEqual(metadata.address_range, address_range)
        self.assertEqual(metadata.memory_size, memory_size)
        self.assertEqual(metadata.permissions, permissions)
        self.assertEqual(metadata.offset, mr.convert_hex_to_int(offset))
        self.assertEqual(metadata.device, device)
        self.assertEqual(metadata.inode, inode)
        self.assertEqual(metadata.path_name, path_name)
        self.assertTrue(metadata.is_readable())
        self.assertTrue(metadata.is_private())
        self.assertTrue(metadata.is_writable())
        self.assertFalse(metadata.is_shared())
        self.assertFalse(metadata.is_executable())

    def test_add_address_space_failure_invalid_line_pattern(self):
        invalid_line = "invalid line pattern"
        self.assertRaises(ValueError, mr.AddressSpaceMetadata, invalid_line)

    def __get_memory_size(self, address_range):
        start_address = mr.convert_hex_to_int(address_range[0])
        end_address = mr.convert_hex_to_int(address_range[1])
        return end_address - start_address


class TestMemoryReader(unittest.TestCase):

    def __init__(self, *args, **kwargs):
        super(TestMemoryReader, self).__init__(*args, **kwargs)
        logging.disable(logging.CRITICAL)

    def setUp(self):
        self.target_pid = 1234
        pid_string = str(self.target_pid)
        self.maps_path = "/proc/" + pid_string + "/maps"
        self.mem_path = "/proc/" + pid_string + "/mem"
        self.syscall_path = "/proc/" + pid_string + "/syscall"
        self.memory_map_line = "7fc981a94000-7fc981a95000 rw-- 00026000 08:06 685615 [stack]"
        self.memory_size = 4096
        self.memory_bytes = bytes([0x06, 0x05, 0x04, 0x03, 0x02, 0x01])
        self.seek_offset = mr.convert_hex_to_int("7fc981a94000")
        self.stack_pointer = "0x7fc981a940ff"

    @patch('builtins.open', return_value=MagicMock())
    def test_MemoryReader(self, context_manager):
        maps_file = self.__mock_maps_file_object(context_manager)

        mr.MemoryReader(self.target_pid)

        self. __verify_read_maps_file_interactions(context_manager, maps_file)

    @patch('builtins.open', return_value=MagicMock())
    def test_MemoryReader_open_IOError(self, context_manager):
        open.side_effect = IOError()

        self.assertRaises(mr.MemoryReaderError,
                          mr.MemoryReader, self.target_pid)

    @patch('builtins.open', return_value=MagicMock())
    def test_MemoryReader_readlines_IOError(self, context_manager):
        maps_file = self.__mock_maps_file_object(context_manager)
        maps_file().readlines.side_effect = IOError()

        self.assertRaises(mr.MemoryReaderError,
                          mr.MemoryReader, self.target_pid)

    @patch('builtins.open', return_value=MagicMock())
    def test_MemoryReader_invalid_maps_line(self, context_manager):
        maps_file = self.__mock_maps_file_object(context_manager)
        invalid_line = "invalid.line"
        maps_file().readlines.return_value = invalid_line

        self.assertRaises(mr.MemoryReaderError,
                          mr.MemoryReader, self.target_pid)

    @patch('builtins.open', return_value=MagicMock())
    def test_read_memory(self, context_manager):
        reader = self.__initialize_reader(context_manager)

        mem_file = self.__mock_mem_file_object(context_manager)
        memory_maps = reader.read_memory()

        self.__assert_memory_map(memory_maps[0])
        self.__verify_read_mem_file_interactions(context_manager, mem_file)

    @patch('builtins.open', return_value=MagicMock())
    def test_read_memory_open_IOError(self, context_manager):
        reader = self.__initialize_reader(context_manager)

        open.side_effect = IOError()
        memory_maps = reader.read_memory()
        self.__assert_empty_memory_map(memory_maps[0])

    @patch('builtins.open', return_value=MagicMock())
    def test_read_memory_mem_file_seek_IOError(self, context_manager):
        reader = self.__initialize_reader(context_manager)

        mem_file = self.__mock_mem_file_object(context_manager)
        mem_file().seek.side_effect = IOError()
        memory_maps = reader.read_memory()
        self.__assert_empty_memory_map(memory_maps[0])

    @patch('builtins.open', return_value=MagicMock())
    def test_read_memory_mem_file_read_IOError(self, context_manager):
        reader = self.__initialize_reader(context_manager)

        mem_file = self.__mock_mem_file_object(context_manager)
        mem_file().seek.side_effect = IOError()
        memory_maps = reader.read_memory()
        self.__assert_empty_memory_map(memory_maps[0])

    @patch('builtins.open', return_value=MagicMock())
    def test_read_current_call_stack(self, context_manager):
        stack_pointer_reader = self.__mock_stack_pointer_reader()
        self.seek_offset = mr.convert_hex_to_int(self.stack_pointer)
        self.memory_size = 3841
        reader = self.__initialize_reader(
            context_manager, stack_pointer_reader)

        file = self.__mock_mem_file_object(context_manager)

        actual_stack_pointer, memory_map = reader.read_current_call_stack()

        self.assertEqual(actual_stack_pointer, self.stack_pointer)
        self.__assert_memory_map(memory_map)
        self.__verify_stack_pointer_reader_interaction(stack_pointer_reader)
        self.__verify_read_mem_file_interactions(context_manager, file)

    @patch('builtins.open', return_value=MagicMock())
    def test_read_current_call_stack_open_IOError(self, context_manager):
        stack_pointer_reader = self.__mock_stack_pointer_reader()
        reader = self.__initialize_reader(
            context_manager, stack_pointer_reader)

        open.side_effect = IOError()
        self.assertRaises(mr.MemoryReaderError, reader.read_current_call_stack)

    @patch('builtins.open', return_value=MagicMock())
    def test_read_current_call_stack_StackPointerReaderError(self, context_manager):
        stack_pointer_reader = self.__mock_stack_pointer_reader()
        stack_pointer_reader.read_stack_pointer.side_effect = StackPointerReaderError()
        reader = self.__initialize_reader(
            context_manager, stack_pointer_reader)

        file = self.__mock_mem_file_object(context_manager)

        self.assertRaises(mr.MemoryReaderError, reader.read_current_call_stack)

    @patch('builtins.open', return_value=MagicMock())
    def test_read_current_call_stack_mem_seek_IOError(self, context_manager):
        stack_pointer_reader = self.__mock_stack_pointer_reader()
        reader = self.__initialize_reader(
            context_manager, stack_pointer_reader)

        file = self.__mock_mem_file_object(context_manager)
        file().seek.side_effect = IOError()

        self.assertRaises(mr.MemoryReaderError, reader.read_current_call_stack)

    @patch('builtins.open', return_value=MagicMock())
    def test_read_current_call_stack_mem_read_IOError(self, context_manager):
        stack_pointer_reader = self.__mock_stack_pointer_reader()
        reader = self.__initialize_reader(
            context_manager, stack_pointer_reader)

        file = self.__mock_mem_file_object(context_manager)
        file().read.side_effect = IOError()

        self.assertRaises(mr.MemoryReaderError, reader.read_current_call_stack)

    def __initialize_reader(self, context_manager, stack_pointer_reader=None):
        maps_file = self.__mock_maps_file_object(context_manager)
        reader = mr.MemoryReader(self.target_pid, stack_pointer_reader)
        self.__verify_read_maps_file_interactions(context_manager, maps_file)

        return reader

    def __mock_mem_file_object(self, context_manager):
        mocked_file = MagicMock()
        context_manager().__enter__.return_value = mocked_file()
        mocked_file().read.return_value = self.memory_bytes

        return mocked_file

    def __mock_maps_file_object(self, context_manager):
        mocked_file = MagicMock()
        context_manager().__enter__.return_value = mocked_file()
        mocked_file().readlines.return_value = [self.memory_map_line]

        return mocked_file

    def __mock_stack_pointer_reader(self):
        stack_pointer_reader = MagicMock()
        stack_pointer_reader.read_stack_pointer.return_value = self.stack_pointer

        return stack_pointer_reader

    def __assert_memory_map(self, actual_memory_map):
        expected_metadata = mr.AddressSpaceMetadata(self.memory_map_line)
        self.assertEqual(actual_memory_map.metadata, expected_metadata)
        self.assertEqual(actual_memory_map.memory_bytes, self.memory_bytes)

    def __assert_empty_memory_map(self, actual_memory_map):
        expected_metadata = mr.AddressSpaceMetadata(self.memory_map_line)
        self.assertEqual(actual_memory_map.metadata, expected_metadata)
        self.assertEqual(actual_memory_map.memory_bytes, bytes(0))

    def __verify_read_mem_file_interactions(self, context_manager, mem_file):
        open_calls = [call(self.mem_path, "rb")]
        open.assert_has_calls(open_calls)
        mem_file().seek.assert_called_once_with(self.seek_offset)
        mem_file().read.assert_called_once_with(self.memory_size)
        context_manager().__exit__.assert_has_calls([call(None, None, None),
                                                     call(None, None, None)])

    def __verify_read_maps_file_interactions(self, context_manager, maps_file):
        open.assert_has_calls([call(self.maps_path)])
        maps_file().readlines.assert_called_once_with()
        context_manager().__enter__.assert_called_once_with()
        context_manager().__exit__.assert_called_once_with(None, None, None)

    def __verify_stack_pointer_reader_interaction(self, stack_pointer_reader):
        stack_pointer_reader.read_stack_pointer.assert_called_once_with(
            self.target_pid)


if __name__ == '__main__':
    unittest.main()
