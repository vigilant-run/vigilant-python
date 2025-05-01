import sys
from typing import Callable
from vigilant.types import LogLevel, Log
from datetime import datetime


class Passthrough:
    """
    Passthrough is a class that passthroughs logs to stdout or stderr.
    """

    stdout_write: Callable[[str], None]
    stderr_write: Callable[[str], None]

    def __init__(self):
        self.stdout_write = sys.stdout.write
        self.stderr_write = sys.stderr.write

    def log_passthrough(self, log: Log):
        match log.level:
            case LogLevel.ERROR:
                self.stderr_write(self._format_log(log) + "\n")
            case _:
                self.stdout_write(self._format_log(log) + "\n")

    def _format_log(self, log: Log) -> str:
        timestamp_str = self._format_timestamp(log.timestamp)
        attributes_str = ""
        for key, value in log.attributes.items():
            attributes_str += f"{key}={value} "
        level_str = log.level
        body_str = log.body
        return f"[{timestamp_str}] [{level_str}] {body_str} {attributes_str}".strip()

    def _format_timestamp(self, timestamp: datetime) -> str:
        return timestamp.strftime("%Y-%m-%d %H:%M:%S")
