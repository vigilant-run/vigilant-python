import sys
from typing import Callable
from vigilant.types import LogLevel, Log
from vigilant.utils import create_log_instance


class LogRouter:
    """
    LogRouter is a class that re-routes stdout and stderr to the log function.
    """
    stdout_write: Callable[[str], None]
    stderr_write: Callable[[str], None]
    _stdout_buffer: str
    _stderr_buffer: str
    _log_function: Callable[[Log], None]

    def __init__(self, log_function: Callable[[Log], None]):
        self.stdout_write = sys.stdout.write
        self.stderr_write = sys.stderr.write
        self._stdout_buffer = ""
        self._stderr_buffer = ""
        self._log_function = log_function

    def enable(self):
        sys.stdout.write = self._stdout_write
        sys.stderr.write = self._stderr_write

    def disable(self):
        sys.stdout.write = self.stdout_write
        sys.stderr.write = self.stderr_write

    def _stdout_write(self, message):
        self._stdout_buffer += message
        if '\n' in self._stdout_buffer:
            lines = self._stdout_buffer.split('\n')
            for line in lines[:-1]:
                self._log_function(
                    create_log_instance(line, LogLevel.INFO, {}))
            self._stdout_buffer = lines[-1]

    def _stderr_write(self, message):
        self._stderr_buffer += message
        if '\n' in self._stderr_buffer:
            lines = self._stderr_buffer.split('\n')
            for line in lines[:-1]:
                self._log_function(
                    create_log_instance(line, LogLevel.ERROR, {}))
            self._stderr_buffer = lines[-1]
