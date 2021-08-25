import argparse
import logging
import sys
from memvis import MemvisController
import time


def get_argument_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--start-address",
                        dest="start_address", type=str,
                        help="Address to start visualizing from." +
                        " If not set the current stack pointer will be used.")
    parser.add_argument("-p", "--pid", dest="target_pid", type=int,
                        help="The pid of the process.", required=True)
    parser.add_argument("-n", "--no-ptrace", dest="use_ptrace", action="store_false",
                        help="If set then the stack pointer will " +
                        "be read from /proc/[pid]/syscall file." +
                        " If not set the current stack pointer will be used.")
    parser.add_argument("-j", "--width", dest="width", type=int,
                        help="Window width.", default=10)
    parser.add_argument("-i", "--height", dest="height", type=int,
                        help="Window height.", default=26)
    parser.add_argument("-b", "--print-bytes", dest="convert_ascii",
                        help="If set memvis will not convert bytes to readable ascii characters.",
                        action="store_false")

    return parser


def verify_arguments(args):
    pass


def run():
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    fh = logging.FileHandler("memvis.log", "w")
    fh.setFormatter(formatter)
    err = open("memvis.err", "a")

    logger.addHandler(fh)
    argument_parser = get_argument_parser()
    args = argument_parser.parse_args()
    verify_arguments(args)

    sys.stderr = err
    controller = MemvisController(
        args.target_pid, width=args.width, height=args.height,
        start_address=args.start_address, use_ptrace=args.use_ptrace,
        convert_ascii=args.convert_ascii)
    controller.start()


if __name__ == "__main__":
    run()
