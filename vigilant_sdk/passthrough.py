import sys
from typing import Callable
from vigilant_sdk.types import LogLevel, Log
from datetime import datetime


class EventPassthrough:
    stdout_write: Callable[[str], None]
    stderr_write: Callable[[str], None]

    def __init__(self):
        self.stdout_write = sys.stdout.write
        self.stderr_write = sys.stderr.write

    def log_passthrough(self, log: Log):
        match log['level']:
            case LogLevel.ERROR:
                self.stderr_write(self._format_log(log) + "\n")
            case _:
                self.stdout_write(self._format_log(log) + "\n")

    def _format_log(self, log: Log) -> str:
        timestamp_str = self._format_timestamp(log.get('timestamp', ''))
        attributes_str = ""
        for key, value in log.get("attributes", {}).items():
            attributes_str += f"{key}={value} "
        level_str = log.get('level', '')
        body_str = log.get('body', '')
        return f"[{timestamp_str}] [{level_str}] {body_str} {attributes_str}".strip()

    def _format_timestamp(self, timestamp_str: str) -> str:
        try:
            dt_obj = datetime.fromisoformat(
                timestamp_str.replace('Z', '+00:00'))
            return dt_obj.strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            return timestamp_str
