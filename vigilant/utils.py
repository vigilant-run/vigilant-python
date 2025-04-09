from datetime import datetime, timezone
from typing import Dict
from vigilant.types import LogLevel, Log


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
