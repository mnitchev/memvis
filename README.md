# memvis

Memvis is a process memory visualizer. It will attempt to read all of the
memory pages of a process and print the memory data in a table format, where
each address's data is presented in hex format. If an address' value is an
ascii character, memvis will by default print the ascii character (this can be
turned off).

This tool is intended to help with performing a [Stack Buffer
Overflow](https://en.wikipedia.org/wiki/Stack_buffer_overflow), which is why
the stack is opened first by default when running memvis. However all the
mapped memory regions are read and can be visualized. To learn more about what
maps are available and how they are read see
[/proc/[pid]/maps](https://man7.org/linux/man-pages/man5/proc.5.html) and
[/proc/[pid]/mem](https://man7.org/linux/man-pages/man5/proc.5.html).

## Usage

```
usage: memvis [-h] [-s START_ADDRESS] -p TARGET_PID [-n] [-j WIDTH] [-i HEIGHT] [-b]

optional arguments:
  -h, --help            show this help message and exit
  -s START_ADDRESS, --start-address START_ADDRESS
                        Address to start visualizing from. If not set the current stack pointer will be used.
  -p TARGET_PID, --pid TARGET_PID
                        The pid of the process.
  -n, --no-ptrace       If set then the stack pointer will be read from /proc/[pid]/syscall file. If not set the current stack pointer will be used.
  -j WIDTH, --width WIDTH
                        Window width.
  -i HEIGHT, --height HEIGHT
                        Window height.
  -b, --print-bytes     If set memvis will not convert bytes to readable asii characters.

c
```

## Controls

| Button | Function                                                                                     |
| ------ | -------------------------------------------------------------------------------------------- |
| Up     | Move address space up one byte (subtract one byte)                                           |
| Down   | Move address space down one byte (add one byte)                                              |
| Left   | Previous mapped memory region. Order is determined by `/proc/[pid]/maps`                     |
| Right  | Next mapped memory region. Order is determined by `/proc/[pid]/maps`                         |
| j      | Jump to address. When pressed user is prompted to enter an address and hit `Enter` when done |
| q      | Exit memvis                                                                                  |

## Demo

[![asciicast](https://asciinema.org/a/2kkflprFvhwt5QNrKylCAm0Da.svg)](https://asciinema.org/a/2kkflprFvhwt5QNrKylCAm0Da)
