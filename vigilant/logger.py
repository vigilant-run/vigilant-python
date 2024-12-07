from enum import Enum
import time
import inspect
from typing import Optional, List, Dict, Any
from opentelemetry.sdk._logs import LoggerProvider
from opentelemetry.sdk._logs.export import BatchLogProcessor
from opentelemetry._logs import Logger as OTELLogger
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.semconv.resource import ResourceAttributes


class LogLevel(str, Enum):
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"
    DEBUG = "DEBUG"


class LoggerOptions:
    def __init__(self):
        self.otel_logger: Optional[OTELLogger] = None
        self.name: str = ""
        self.attributes: List[Dict[str, Any]] = []
        self.url: str = ""
        self.token: str = ""
        self.passthrough: bool = False
        self.insecure: bool = False


class Logger:
    def __init__(self, options: LoggerOptions):
        self.otel_logger = self._get_otel_logger(options)
        self.attributes = options.attributes
        self.passthrough = options.passthrough

    def debug(self, message: str, **attrs):
        caller_attrs = self._get_caller_attrs()
        self._log(LogLevel.DEBUG, message, None, {**attrs, **caller_attrs})
        if self.passthrough:
            print(message)

    def info(self, message: str, **attrs):
        caller_attrs = self._get_caller_attrs()
        self._log(LogLevel.INFO, message, None, {**attrs, **caller_attrs})
        if self.passthrough:
            print(message)

    def warn(self, message: str, **attrs):
        caller_attrs = self._get_caller_attrs()
        self._log(LogLevel.WARN, message, None, {**attrs, **caller_attrs})
        if self.passthrough:
            print(message)

    def error(self, message: str, error: Optional[Exception] = None, **attrs):
        caller_attrs = self._get_caller_attrs()
        attrs_with_error = attrs
        if error:
            attrs_with_error['error'] = str(error)
        self._log(LogLevel.ERROR, message, error, {
                  **attrs_with_error, **caller_attrs})
        if self.passthrough:
            print(message)

    def _log(self, level: LogLevel, message: str, error: Optional[Exception], attrs: Dict[str, Any]):
        self.otel_logger.emit(
            severity=self._get_severity(level),
            body=message,
            attributes=attrs,
            timestamp=int(time.time() * 1e9)  # nanoseconds
        )

    @staticmethod
    def _get_severity(level: LogLevel) -> str:
        return level.value

    @staticmethod
    def _get_caller_attrs() -> Dict[str, Any]:
        frame = inspect.currentframe()
        caller = frame.f_back.f_back
        return {
            'caller.file': caller.f_code.co_filename,
            'caller.line': caller.f_lineno,
            'caller.function': caller.f_code.co_name
        }

    def _get_otel_logger(self, options: LoggerOptions) -> OTELLogger:
        if options.otel_logger:
            return options.otel_logger

        name = options.name or "example"
        url = options.url or "log.vigilant.run:4317"
        token = options.token or "tk_1234567890"

        exporter = OTLPLogExporter(
            endpoint=url,
            headers={"x-vigilant-token": token},
            insecure=options.insecure
        )

        resource = Resource.create({
            ResourceAttributes.SERVICE_NAME: name
        })

        provider = LoggerProvider(
            resource=resource,
            processors=[BatchLogProcessor(exporter)]
        )

        return provider.get_logger(name)


def create_logger(**kwargs) -> Logger:
    options = LoggerOptions()
    options.name = kwargs.get('name', '')
    options.url = kwargs.get('url', '')
    options.token = kwargs.get('token', '')
    options.passthrough = kwargs.get('passthrough', False)
    options.insecure = kwargs.get('insecure', False)
    options.attributes = kwargs.get('attributes', [])
    return Logger(options)
