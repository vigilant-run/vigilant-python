from enum import Enum
import time
import inspect
import traceback
from typing import Optional, List, Dict, Any
from opentelemetry.sdk._logs import LoggerProvider, LogRecord
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.semconv.resource import ResourceAttributes
from opentelemetry._logs import SeverityNumber
from opentelemetry._logs import Logger as OTELLogger


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
        otel_provider (Optional[LoggerProvider]): Optional custom LoggerProvider instance
        otel_logger (Optional[OTELLogger]): Optional custom Logger instance
    """

    def __init__(self):
        self.otel_provider: Optional[LoggerProvider] = None
        self.otel_logger: Optional[OTELLogger] = None
        self.name: str = "service"
        self.attributes: List[Dict[str, Any]] = []
        self.url: str = "log.vigilant.run:4317"
        self.token: str = "tk_1234567890"
        self.passthrough: bool = True
        self.disabled: bool = False
        self.insecure: bool = False


class Logger:
    def __init__(self, options: LoggerOptions):
        self.otel_provider = self._get_logger_provider(options)
        self.otel_logger = self.otel_provider.get_logger(options.name)
        self.attributes = options.attributes
        self.passthrough = options.passthrough

    def debug(self, message: str, attrs: Dict[str, Any] = {}):
        """
        Log a debug message

        Args:
            message: The message to log
            attrs: Additional attributes to include with the log
        """
        caller_attrs = self._get_caller_attrs()
        self._log(LogLevel.DEBUG, message, None, {**attrs, **caller_attrs})
        if self.passthrough:
            print(message)

    def info(self, message: str, attrs: Dict[str, Any] = {}):
        """
        Log an info message

        Args:
            message: The message to log
            attrs: Additional attributes to include with the log
        """
        caller_attrs = self._get_caller_attrs()
        self._log(LogLevel.INFO, message, None, {**attrs, **caller_attrs})
        if self.passthrough:
            print(message)

    def warn(self, message: str, attrs: Dict[str, Any] = {}):
        """
        Log a warning message

        Args:
            message: The message to log
            attrs: Additional attributes to include with the log
        """
        caller_attrs = self._get_caller_attrs()
        self._log(LogLevel.WARN, message, None, {**attrs, **caller_attrs})
        if self.passthrough:
            print(message)

    def error(self, message: str, attrs: Dict[str, Any] = {}, error: Optional[Exception] = None):
        """
        Log an error message

        Args:
            message: The message to log
            attrs: Additional attributes to include with the log
            error: An optional exception to include with the log
        """
        caller_attrs = self._get_caller_attrs()
        attrs_with_error = attrs
        if error:
            attrs_with_error['error'] = str(error)
        self._log(LogLevel.ERROR, message, error, {
                  **attrs_with_error, **caller_attrs})
        if self.passthrough:
            print(message)

    @staticmethod
    def _get_severity(level: LogLevel) -> str:
        return level.value

    @staticmethod
    def _get_severity_number(level: LogLevel) -> SeverityNumber:
        severity_map = {
            LogLevel.DEBUG: SeverityNumber.DEBUG,
            LogLevel.INFO: SeverityNumber.INFO,
            LogLevel.WARN: SeverityNumber.WARN,
            LogLevel.ERROR: SeverityNumber.ERROR,
        }
        return severity_map.get(level, SeverityNumber.INFO)

    @staticmethod
    def _get_caller_attrs() -> Dict[str, Any]:
        frame = inspect.currentframe()
        try:
            caller = frame.f_back.f_back
            if caller is None:
                return {}
            return {
                'caller.file': caller.f_code.co_filename,
                'caller.line': caller.f_lineno,
                'caller.function': caller.f_code.co_name
            }
        finally:
            del frame

    def _get_logger_provider(self, options: LoggerOptions) -> LoggerProvider:
        if options.otel_provider:
            return options.otel_provider

        name = options.name
        url = options.url
        token = options.token

        exporter = OTLPLogExporter(
            endpoint=url,
            headers={"x-vigilant-token": token},
            insecure=options.insecure
        )

        resource = Resource.create({
            ResourceAttributes.SERVICE_NAME: name
        })

        provider = LoggerProvider(resource=resource)
        provider.add_log_record_processor(BatchLogRecordProcessor(exporter))

        return provider

    def _log(self, level: LogLevel, message: str, error: Optional[Exception], attrs: Dict[str, Any]):
        attributes = attrs.copy()
        if error:
            attributes.update({
                'error.type': error.__class__.__name__,
                'error.message': str(error),
                'error.stack': getattr(error, '__traceback__', None) and ''.join(traceback.format_tb(error.__traceback__))
            })

        record = LogRecord(
            timestamp=int(time.time() * 1e9),
            severity_text=self._get_severity(level),
            severity_number=self._get_severity_number(level),
            body=message,
            attributes=attributes,
            resource=self.otel_provider.resource,
            trace_id=0,
            span_id=0,
            trace_flags=0,
        )

        self.otel_logger.emit(record)


def create_logger(
    *,
    url: str,
    token: str,
    name: str,
    passthrough: bool = True,
    insecure: bool = False,
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
    return Logger(options)


class NoopLogger:
    def __init__(self):
        pass

    def debug(self, message: str, attrs: Dict[str, Any] = {}):
        """
        Log a debug message

        Args:
            message: The message to log
            attrs: Additional attributes to include with the log
        """
        print(message, attrs)

    def info(self, message: str, attrs: Dict[str, Any] = {}):
        """
        Log an info message

        Args:
            message: The message to log
            attrs: Additional attributes to include with the log
        """
        print(message, attrs)

    def warn(self, message: str, attrs: Dict[str, Any] = {}):
        """
        Log a warning message

        Args:
            message: The message to log
            attrs: Additional attributes to include with the log
        """
        print(message, attrs)

    def error(self, message: str, attrs: Dict[str, Any] = {}, error: Optional[Exception] = None):
        """
        Log an error message

        Args:
            message: The message to log
            attrs: Additional attributes to include with the log
            error: An optional exception to include with the log
        """
        print(message, attrs, error)


def create_noop_logger() -> NoopLogger:
    return NoopLogger()
