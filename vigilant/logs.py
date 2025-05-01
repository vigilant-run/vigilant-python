from typing import Dict
from vigilant.message import NotInitializedError
from vigilant.types import LogLevel, Log
from vigilant.instance import get_global_instance


def log_info(message: str, attributes: Dict[str, str] = {}):
    """
    Logs an info message.

    Args:
        message (str): The message to log.
        attributes (Dict[str, str]): The attributes to log.

    Usage:
        log_info("This is an info message", {"user.id": "1234"})
    """
    global_instance = get_global_instance()
    if global_instance is None:
        raise NotInitializedError()

    log = Log(message, LogLevel.INFO, attributes)

    global_instance.send_log(log)


def log_error(message: str, attributes: Dict[str, str] = {}):
    """
    Logs an error message.

    Args:
        message (str): The message to log.
        attributes (Dict[str, str]): The attributes to log.

    Usage:
        log_error("This is an error message", {"user.id": "1234"})
    """
    global_instance = get_global_instance()
    if global_instance is None:
        raise NotInitializedError()

    log = Log(message, LogLevel.ERROR, attributes)

    global_instance.send_log(log)


def log_warn(message: str, attributes: Dict[str, str] = {}):
    """
    Logs a warning message.

    Args:
        message (str): The message to log.
        attributes (Dict[str, str]): The attributes to log.

    Usage:
        log_warn("This is a warning message", {"user.id": "1234"})
    """
    global_instance = get_global_instance()
    if global_instance is None:
        raise NotInitializedError()

    log = Log(message, LogLevel.WARN, attributes)

    global_instance.send_log(log)


def log_debug(message: str, attributes: Dict[str, str] = {}):
    """
    Logs a debug message.

    Args:
        message (str): The message to log.
        attributes (Dict[str, str]): The attributes to log.

    Usage:
        log_debug("This is a debug message", {"user.id": "1234"})
    """
    global_instance = get_global_instance()
    if global_instance is None:
        raise NotInitializedError()

    log = Log(message, LogLevel.DEBUG, attributes)

    global_instance.send_log(log)


def log_trace(message: str, attributes: Dict[str, str] = {}):
    """
    Logs a trace message.

    Args:
        message (str): The message to log.
        attributes (Dict[str, str]): The attributes to log.

    Usage:
        log_trace("This is a trace message", {"user.id": "1234"})
    """
    global_instance = get_global_instance()
    if global_instance is None:
        raise NotInitializedError()

    log = Log(message, LogLevel.TRACE, attributes)

    global_instance.send_log(log)
