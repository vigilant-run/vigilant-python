from datetime import datetime, timezone
from typing import Dict
from vigilant_sdk.types import LogLevel, Log, Alert


def get_current_timestamp():
    return datetime.now(timezone.utc).isoformat(timespec='microseconds').replace('+00:00', 'Z')


def create_log_instance(message: str, level: LogLevel,
                        attributes: Dict[str, str] = {}) -> Log:
    """
    Creates a log instance.
    """
    return {
        "timestamp": get_current_timestamp(),
        "body": message,
        "level": level,
        "attributes": attributes
    }


def create_alert_instance(title: str, attributes: Dict[str, str] = {}) -> Alert:
    """
    Creates an alert instance.
    """
    return {
        "timestamp": get_current_timestamp(),
        "title": title,
        "attributes": attributes
    }
