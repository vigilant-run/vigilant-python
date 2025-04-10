import sys
from typing import Callable
from vigilant_sdk.types import LogLevel, Log


class LogPassthrough:
    stdout_write: Callable[[str], None]
    stderr_write: Callable[[str], None]

    def __init__(self):
        self.stdout_write = sys.stdout.write
        self.stderr_write = sys.stderr.write

    def passthrough(self, log: Log):
        match log['level']:
            case LogLevel.ERROR:
                self.stderr_write(log['body'])
            case _:
                self.stdout_write(log['body'])
