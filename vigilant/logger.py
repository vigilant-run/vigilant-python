from enum import Enum
import time
import traceback
from typing import Optional, List, Dict, Any
from vigilant.context import get_attributes
from opentelemetry.sdk._logs import LoggerProvider, LogRecord
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.semconv.resource import ResourceAttributes
from opentelemetry._logs import SeverityNumber


class LogLevel(str, Enum):
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"
    DEBUG = "DEBUG"


class LoggerOptions:
    """Configuration options for the Logger.

    Attributes:
        name (str): Name of the service you are logging from. Used as service.name in logs.
        url (str): The URL of the logging endpoint (e.g., 'log.vigilant.run:4317')
        token (str): Authentication token for the logging service
        passthrough (bool): Whether to also print logs to stdout
        insecure (bool): Whether to use insecure connection for gRPC
        attributes (List[Dict[str, Any]]): Additional attributes to include with all logs
    """

    def __init__(self):
        self.name: str = "service"
        self.attributes: List[Dict[str, Any]] = []
        self.url: str = "log.vigilant.run:4317"
        self.token: str = "tk_1234567890"
        self.passthrough: bool = True
        self.noop: bool = False
        self.insecure: bool = False


class Logger:
    def __init__(self, options: LoggerOptions):
        self.name = options.name
        self.attributes = options.attributes
        self.passthrough = options.passthrough
        self.noop = options.noop
        self.otel_exporter = self._get_exporter(options)
        self.otel_provider = self._get_logger_provider()
        self.otel_logger = self.otel_provider.get_logger(self.name)

    def debug(self, message: str, attrs: Dict[str, Any] = {}):
        """
        Log a debug message

        Args:
            message: The message to log
            attrs: Additional attributes to include with the log
        """
        caller_attrs = self._get_call_stack()
        self._log(LogLevel.DEBUG, message, None, {**attrs, **caller_attrs})
        self._passthrough(message)

    def info(self, message: str, attrs: Dict[str, Any] = {}):
        """
        Log an info message

        Args:
            message: The message to log
            attrs: Additional attributes to include with the log
        """
        caller_attrs = self._get_call_stack()
        self._log(LogLevel.INFO, message, None, {**attrs, **caller_attrs})
        self._passthrough(message)

    def warn(self, message: str, attrs: Dict[str, Any] = {}):
        """
        Log a warning message

        Args:
            message: The message to log
            attrs: Additional attributes to include with the log
        """
        caller_attrs = self._get_call_stack()
        self._log(LogLevel.WARN, message, None, {**attrs, **caller_attrs})
        self._passthrough(message)

    def error(self, message: str, attrs: Dict[str, Any] = {}, error: Optional[Exception] = None):
        """
        Log an error message

        Args:
            message: The message to log
            attrs: Additional attributes to include with the log
            error: An optional exception to include with the log
        """
        caller_attrs = self._get_call_stack()
        attrs_with_error = attrs
        if error:
            attrs_with_error['error'] = str(error)
        self._log(LogLevel.ERROR, message, error, {
                  **attrs_with_error, **caller_attrs})
        self._passthrough(message)

    def _passthrough(self, message: str):
        if self.passthrough:
            print(message)

    def _get_severity(self, level: LogLevel) -> str:
        return level.value

    def _get_severity_number(self, level: LogLevel) -> SeverityNumber:
        severity_map = {
            LogLevel.DEBUG: SeverityNumber.DEBUG,
            LogLevel.INFO: SeverityNumber.INFO,
            LogLevel.WARN: SeverityNumber.WARN,
            LogLevel.ERROR: SeverityNumber.ERROR,
        }
        return severity_map.get(level, SeverityNumber.INFO)

    def _get_call_stack(self) -> Dict[str, Any]:
        stack = traceback.extract_stack()[:-2]
        formatted_stack = "Traceback (most recent call last):\n" + "\n".join(
            f'  File "{frame.filename}", line {frame.lineno}, in {frame.name}\n\t{frame.line}'
            for frame in reversed(stack)
        )
        frame = stack[-1]
        return {
            'process.stack': formatted_stack,
            'caller.file': frame.filename,
            'caller.line': frame.lineno,
            'caller.function': frame.name,
        }

    def _get_exporter(self, options: LoggerOptions) -> OTLPLogExporter:
        url = options.url
        token = options.token
        return OTLPLogExporter(
            endpoint=url,
            headers={"x-vigilant-token": token},
            insecure=options.insecure,
            timeout=0
        )

    def _get_logger_provider(self) -> LoggerProvider:
        provider = LoggerProvider()
        provider.add_log_record_processor(
            BatchLogRecordProcessor(self.otel_exporter))
        return provider

    def _log(self, level: LogLevel, message: str, error: Optional[Exception], attrs: Dict[str, Any]):
        if self.noop:
            return

        attributes = attrs.copy()
        if error:
            attributes.update({
                'error.type': error.__class__.__name__,
                'error.message': str(error),
                'error.stack': getattr(error, '__traceback__', None) and ''.join(traceback.format_tb(error.__traceback__))
            })

        additional_attributes = self._get_attributes()
        if additional_attributes:
            attributes.update(additional_attributes)

        resource = Resource.create({
            ResourceAttributes.SERVICE_NAME: self.name
        })

        record = LogRecord(
            timestamp=int(time.time() * 1e9),
            severity_text=self._get_severity(level),
            severity_number=self._get_severity_number(level),
            body=message,
            attributes=attributes,
            resource=resource,
            trace_id=0,
            span_id=0,
            trace_flags=0,
        )

        self.otel_logger.emit(record)

    def _get_attributes(self) -> Dict[str, str]:
        return get_attributes()


def create_logger(
    *,
    url: str,
    token: str,
    name: str,
    passthrough: bool = True,
    insecure: bool = False,
    noop: bool = False,
    attributes: List[Dict[str, Any]] = None,
) -> Logger:
    """Create a new Logger instance for sending logs to Vigilant.

    Args:
        url (str): The URL of the logging endpoint (e.g., 'log.vigilant.run:4317')
        token (str): Authentication token for the logging service
        name (str): Name of the service you are logging from. Used as service.name in logs.
        passthrough (bool, optional): Whether to also print logs to stdout. Defaults to True.
        insecure (bool, optional): Whether to use insecure gRPC connection. Defaults to False.
        noop (bool, optional): Whether to disable logging. Defaults to False.
        attributes (List[Dict[str, Any]], optional): Additional attributes to include with all logs. Defaults to None.

    Returns:
        Logger: A configured logger instance ready to send logs to Vigilant

    Example:
        >>> logger = create_logger(
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
    return Logger(options)
