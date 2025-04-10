from enum import Enum
from typing import TypedDict, Dict
from datetime import datetime
from vigilant_sdk.logs import Log
from vigilant_sdk.vigilant import _global_instance
from vigilant_sdk.message import NotInitializedError


class LogLevel(Enum):
    ERROR = 'ERROR'
    WARN = 'WARN'
    INFO = 'INFO'
    DEBUG = 'DEBUG'
    TRACE = 'TRACE'


class Log(TypedDict):
    timestamp: str
    body: str
    level: LogLevel
    attributes: Dict[str, str]


def log_info(message: str, attributes: Dict[str, str] = {}):
    """
    Log an info message.

    Args:
        message (str): The message to log.
        attributes (Dict[str, str]): The attributes to log.

    Usage:
        log_info("This is an info message", {"user.id": "1234"})
    """
    if _global_instance is None:
        raise NotInitializedError()

    log = create_log_instance(message, LogLevel.INFO, attributes)

    _global_instance.log_batcher.add(log)


def log_error(message: str, attributes: Dict[str, str] = {}):
    """
    Log an error message.

    Args:
        message (str): The message to log.
        attributes (Dict[str, str]): The attributes to log.

    Usage:
        log_error("This is an error message", {"user.id": "1234"})
    """
    if _global_instance is None:
        raise NotInitializedError()

    log = create_log_instance(message, LogLevel.ERROR, attributes)

    _global_instance.log_batcher.add(log)


def log_warn(message: str, attributes: Dict[str, str] = {}):
    """
    Log a warning message.

    Args:
        message (str): The message to log.
        attributes (Dict[str, str]): The attributes to log.

    Usage:
        log_warn("This is a warning message", {"user.id": "1234"})
    """
    if _global_instance is None:
        raise NotInitializedError()

    log = create_log_instance(message, LogLevel.WARN, attributes)

    _global_instance.log_batcher.add(log)


def log_debug(message: str, attributes: Dict[str, str] = {}):
    """
    Log a debug message.

    Args:
        message (str): The message to log.
        attributes (Dict[str, str]): The attributes to log.

    Usage:
        log_debug("This is a debug message", {"user.id": "1234"})
    """
    if _global_instance is None:
        raise NotInitializedError()

    log = create_log_instance(message, LogLevel.DEBUG, attributes)

    _global_instance.log_batcher.add(log)


def log_trace(message: str, attributes: Dict[str, str] = {}):
    """
    Log a trace message.

    Args:
        message (str): The message to log.
        attributes (Dict[str, str]): The attributes to log.

    Usage:
        log_trace("This is a trace message", {"user.id": "1234"})
    """
    if _global_instance is None:
        raise NotInitializedError()

    log = create_log_instance(message, LogLevel.TRACE, attributes)

    _global_instance.log_batcher.add(log)


def create_log_instance(message: str, level: LogLevel,
                        attributes: Dict[str, str] = {}) -> Log:
    """
    Creates a log instance.
    """
    return {
        "timestamp": datetime.now().isoformat(timespec='nanoseconds'),
        "body": message,
        "level": level,
        "attributes": attributes
    }
