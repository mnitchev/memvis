import time
import curses
import logging
import argparse
import threading
import prettytable
from ..memory import convert_hex_to_int
from .console_memory_table import ConsoleMemoryTable

UP = 259
DOWN = 258
LEFT = 260
RIGHT = 261
JUMP = 106


class Console:
    def __init__(self, target_pid, start_address, memory_reference, page_height=35,
                 page_width=12, convert_ascii=True, frame_rate=10):
        self._log = logging.getLogger(self.__class__.__name__)
        self.target_pid = target_pid
        self.memory_reference = memory_reference
        self.start_address = start_address
        self.page_height = page_height
        self.page_width = page_width
        self.memory_table = ConsoleMemoryTable(
            start_address, height=page_height, width=page_width, convert_ascii=convert_ascii)
        self.end_address = self.memory_table.end_address
        self.standard_source = curses.initscr()
        self.current_address_space_index = 0
        self.running = False
        self.frame_rate = frame_rate

    def start(self):
        self._log.info("Starting console UI.")
        self.running = True
        self.key = ''
        self.standard_source.nodelay(1)
        curses.cbreak()
        curses.curs_set(0)
        pad = curses.newwin(curses.LINES, curses.COLS, 1, 3)
        while self.key not in [ord('q'), ord('Q')]:
            self.standard_source.keypad(1)
            self.key = self.standard_source.getch()
            curses.flushinp()

            if self.key == UP:
                self.__increment_address(-1)
            if self.key == DOWN:
                self.__increment_address(1)

            if self.key == LEFT:
                self.__change_page(-1)
            if self.key == RIGHT:
                self.__change_page(1)

            index, metadata, memory_bytes = self.memory_reference.get_range(
                self.start_address, self.end_address)
            self.current_address_space_index = index
            self.memory_table.set_memory_bytes(
                self.start_address, metadata, memory_bytes)
            tableStr = self.memory_table.draw()

            pad.addstr(tableStr)
            pad.refresh()

            pad.move(0, 0)
            if self.key == JUMP:
                self.__jump_to_address(pad)
            time.sleep(1 / self.frame_rate)

    def __jump_to_address(self, pad):
        curses.echo()
        curses.nocbreak()
        curses.curs_set(1)
        self.standard_source.addstr(10, 10, "Input address to jump to: ")
        self.standard_source.nodelay(0)
        self.standard_source.refresh()
        jump_address = self.standard_source.getstr(11, 10, 14).decode("utf-8")
        self.standard_source.refresh()
        try:
            jump_address_int = convert_hex_to_int(jump_address)
            self.__jump_start_address_to(jump_address_int)
        except ValueError:
            print("Wrong input! " + str(len(jump_address)))
            time.sleep(0.5)

        self.standard_source.nodelay(1)
        curses.noecho()
        curses.cbreak()
        curses.curs_set(0)

    def __change_page(self, amount):
        address_ranges = self.memory_reference.address_ranges
        self.current_address_space_index += amount
        if self.current_address_space_index < 0:
            self.current_address_space_index = 0
        if self.current_address_space_index >= len(address_ranges):
            self.current_address_space_index = len(address_ranges) - 1
        space = address_ranges[self.current_address_space_index]
        self.__jump_start_address_to(space.start)

    def __jump_start_address_to(self, address):
        self.start_address = hex(address)
        self.end_address = hex(
            address + self.page_height * self.page_width)

    def __increment_address(self, amount):
        start_int = convert_hex_to_int(self.start_address)
        start_int = start_int + amount * self.page_width
        self.start_address = hex(start_int)
        self.end_address = hex(start_int + self.page_height * self.page_width)

    def __del__(self):
        self._log.info("Destroying console UI.")
        curses.nocbreak()
        self.standard_source.keypad(False)
        curses.curs_set(1)
        curses.echo()
        curses.endwin()
