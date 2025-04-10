from typing import Dict
from vigilant_sdk.message import NotInitializedError
from vigilant_sdk.types import LogLevel
from vigilant_sdk.instance import get_global_instance
from vigilant_sdk.utils import create_log_instance


def log_info(message: str, attributes: Dict[str, str] = {}):
    """
    Log an info message.

    Args:
        message (str): The message to log.
        attributes (Dict[str, str]): The attributes to log.

    Usage:
        log_info("This is an info message", {"user.id": "1234"})
    """
    global_instance = get_global_instance()
    if global_instance is None:
        raise NotInitializedError()

    log = create_log_instance(message, LogLevel.INFO, attributes)

    global_instance.send_log(log)


def log_error(message: str, attributes: Dict[str, str] = {}):
    """
    Log an error message.

    Args:
        message (str): The message to log.
        attributes (Dict[str, str]): The attributes to log.

    Usage:
        log_error("This is an error message", {"user.id": "1234"})
    """
    global_instance = get_global_instance()
    if global_instance is None:
        raise NotInitializedError()

    log = create_log_instance(message, LogLevel.ERROR, attributes)

    global_instance.send_log(log)


def log_warn(message: str, attributes: Dict[str, str] = {}):
    """
    Log a warning message.

    Args:
        message (str): The message to log.
        attributes (Dict[str, str]): The attributes to log.

    Usage:
        log_warn("This is a warning message", {"user.id": "1234"})
    """
    global_instance = get_global_instance()
    if global_instance is None:
        raise NotInitializedError()

    log = create_log_instance(message, LogLevel.WARN, attributes)

    global_instance.send_log(log)


def log_debug(message: str, attributes: Dict[str, str] = {}):
    """
    Log a debug message.

    Args:
        message (str): The message to log.
        attributes (Dict[str, str]): The attributes to log.

    Usage:
        log_debug("This is a debug message", {"user.id": "1234"})
    """
    global_instance = get_global_instance()
    if global_instance is None:
        raise NotInitializedError()

    log = create_log_instance(message, LogLevel.DEBUG, attributes)

    global_instance.send_log(log)


def log_trace(message: str, attributes: Dict[str, str] = {}):
    """
    Log a trace message.

    Args:
        message (str): The message to log.
        attributes (Dict[str, str]): The attributes to log.

    Usage:
        log_trace("This is a trace message", {"user.id": "1234"})
    """
    global_instance = get_global_instance()
    if global_instance is None:
        raise NotInitializedError()

    log = create_log_instance(message, LogLevel.TRACE, attributes)

    global_instance.send_log(log)
