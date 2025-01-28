import sys
import json
import time
import threading
import queue
import requests
from enum import Enum
from typing import Optional, Dict, Any, List
from vigilant.context import get_attributes


class LogLevel(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    DEBUG = "DEBUG"


class Logger:
    def __init__(self,
                 name: str = "app-name",
                 endpoint: str = "ingress.vigilant.run",
                 token: str = "tk_1234567890",
                 passthrough: bool = True,
                 insecure: bool = False,
                 noop: bool = False):
        self.original_stdout_write = sys.stdout.write
        self.original_stderr_write = sys.stderr.write
        self._stdout_buffer = ""
        self._stderr_buffer = ""

        self.name = name
        self.endpoint = endpoint
        self.token = token
        self.passthrough = passthrough
        self.insecure = insecure
        self.noop = noop

        self.logs_queue = queue.Queue(maxsize=1000)
        self.batch_stop = threading.Event()
        self.batch_thread = None
        self._start_batcher()

    def debug(self, message: str, attrs: Dict[str, Any] = None):
        self._log(LogLevel.DEBUG, message, None, attrs or {})

    def info(self, message: str, attrs: Dict[str, Any] = None):
        self._log(LogLevel.INFO, message, None, attrs or {})

    def warn(self, message: str, attrs: Dict[str, Any] = None):
        self._log(LogLevel.WARNING, message, None, attrs or {})

    def error(self, message: str, error: Optional[Exception] = None, attrs: Dict[str, Any] = None):
        self._log(LogLevel.ERROR, message, error, attrs or {})

    def autocapture_enable(self):
        sys.stdout.write = self._stdout_write
        sys.stderr.write = self._stderr_write

    def autocapture_disable(self):
        sys.stdout.write = self.original_stdout_write
        sys.stderr.write = self.original_stderr_write

    def shutdown(self):
        self._stop_batcher()

    def _log(self, level: LogLevel, message: str, error: Optional[Exception], attrs: Dict[str, Any]):
        if self.noop:
            return

        caller_attrs = get_attributes()
        combined_attrs = {**attrs, **caller_attrs}
        if error:
            combined_attrs["error"] = str(error)

        combined_attrs["service.name"] = self.name

        log_record = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time())),
            "body": message,
            "level": level,
            "attributes": combined_attrs,
        }

        try:
            self.logs_queue.put_nowait(log_record)
        except queue.Full:
            pass

        self._passthrough(message)

    def _start_batcher(self):
        self.batch_thread = threading.Thread(
            target=self._run_batcher, daemon=True
        )
        self.batch_thread.start()

    def _stop_batcher(self):
        self.batch_stop.set()

        remaining_logs = []
        while True:
            try:
                log = self.logs_queue.get_nowait()
                remaining_logs.append(log)
            except queue.Empty:
                break

        if remaining_logs:
            self._send_batch(remaining_logs)

        if self.batch_thread is not None:
            self.batch_thread.join()

    def _run_batcher(self):
        max_batch_size = 100
        batch_interval = 0.1
        buffer: List[Dict[str, Any]] = []

        while not self.batch_stop.is_set():
            try:
                record = self.logs_queue.get(timeout=batch_interval)
                if record is not None:
                    buffer.append(record)

                if len(buffer) >= max_batch_size:
                    self._send_batch(buffer)
                    buffer.clear()

            except queue.Empty:
                if buffer:
                    self._send_batch(buffer)
                    buffer.clear()

        if buffer:
            self._send_batch(buffer)

    def _send_batch(self, logs: List[Dict[str, Any]]):
        if not logs or self.noop:
            return

        payload = {
            "token": self.token,
            "type": "logs",
            "logs": logs,
        }

        try:
            headers = {"Content-Type": "application/json"}
            resp = requests.post(
                f"{'http' if self.insecure else 'https'}://{self.endpoint}/api/message",
                data=json.dumps(payload),
                headers=headers,
            )
            resp.raise_for_status()
        except Exception:
            pass

    def _stdout_write(self, message):
        self._stdout_buffer += message
        if '\n' in self._stdout_buffer:
            lines = self._stdout_buffer.split('\n')
            for line in lines[:-1]:
                self._log(LogLevel.INFO, line, None, {})
            self._stdout_buffer = lines[-1]

    def _stderr_write(self, message):
        self._stderr_buffer += message
        if '\n' in self._stderr_buffer:
            lines = self._stderr_buffer.split('\n')
            for line in lines[:-1]:
                self._log(LogLevel.ERROR, line, None, {})
            self._stderr_buffer = lines[-1]

    def _passthrough(self,  message: str):
        if self.passthrough:
            self.original_stdout_write(f"{message}\n")
