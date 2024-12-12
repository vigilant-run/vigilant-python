import sys
from .logger import Logger, LoggerOptions
from typing import List, Dict, Any


class AutocaptureLogger(Logger):
    def __init__(self, options: LoggerOptions):
        super().__init__(options)
        self.original_stdout_write = sys.stdout.write
        self.original_stderr_write = sys.stderr.write
        self._stdout_buffer = ""
        self._stderr_buffer = ""

    def enable(self):
        """
        Enable the logger and start capturing logs
        """
        sys.stdout.write = self._stdout_write
        sys.stderr.write = self._stderr_write

    def disable(self):
        """
        Disable the logger and stop capturing logs
        """
        sys.stdout.write = self.original_stdout_write
        sys.stderr.write = self.original_stderr_write

    def _stdout_write(self, message):
        self._stdout_buffer += message
        if '\n' in self._stdout_buffer:
            lines = self._stdout_buffer.split('\n')
            for line in lines[:-1]:
                self.info(line)
            self._stdout_buffer = lines[-1]

    def _stderr_write(self, message):
        self._stderr_buffer += message
        if '\n' in self._stderr_buffer:
            lines = self._stderr_buffer.split('\n')
            for line in lines[:-1]:
                self.error(line)
            self._stderr_buffer = lines[-1]

    def _passthrough(self, message: str):
        if self.passthrough:
            self.original_stdout_write(message + '\n')


def create_autocapture_logger(
    *,
    url: str,
    token: str,
    name: str,
    passthrough: bool = True,
    insecure: bool = False,
    noop: bool = False,
    attributes: List[Dict[str, Any]] = None,
) -> AutocaptureLogger:
    """Create a new AutocaptureLogger instance.

    Args:
        url (str): The URL of the logging endpoint (e.g., 'log.vigilant.run:4317')
        token (str): Authentication token for the logging service
        name (str): Name of the service you are logging from. Used as service.name in logs.
        passthrough (bool, optional): Whether to also print logs to stdout. Defaults to True.
        insecure (bool, optional): Whether to use insecure gRPC connection. Defaults to False.
        noop (bool, optional): Whether to disable logging. Defaults to False.
        attributes (List[Dict[str, Any]], optional): Additional attributes to include with all logs. Defaults to None.

    Returns:
        AutocaptureLogger: A configured logger instance ready to send logs to Vigilant

    Example:
        >>> logger = create_autocapture_logger(
        ...     url="log.vigilant.run:4317",
        ...     token="your_token",
        ...     name="my-service"
        ... )
        >>> logger.info("Hello, world!")
    """
    options = LoggerOptions()
    options.name = name
    options.url = url
    options.token = token
    options.passthrough = passthrough
    options.insecure = insecure
    options.attributes = attributes or []
    options.noop = noop
    return AutocaptureLogger(options)
