import unittest
import logging
from unittest.mock import patch, call, MagicMock
from memvis.stack_pointer_reader import get_process_syscall_path
from memvis.stack_pointer_reader import PtraceStackPointerReader


class TestUtilities(unittest.TestCase):

    def test_get_process_syscall_path(self):
        target_pid = 4444
        expected_path = "/proc/" + str(target_pid) + "/syscall"
        actual_path = get_process_syscall_path(target_pid)

        self.assertEqual(actual_path, expected_path)
