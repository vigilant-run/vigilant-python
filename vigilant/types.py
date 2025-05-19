from enum import Enum
from typing import Dict, Any
from datetime import datetime
from vigilant.utils import get_current_timestamp


class LogLevel(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    DEBUG = "DEBUG"
    TRACE = "TRACE"


class Log:
    timestamp: datetime
    body: str
    level: LogLevel
    attributes: Dict[str, str]

    def __init__(self, body: str, level: LogLevel, attributes: Dict[str, str]):
        self.timestamp = get_current_timestamp()
        self.body = body
        self.level = level
        self.attributes = attributes

    def __str__(self) -> str:
        attributes_str = ""
        for key, value in self.attributes.items():
            attributes_str += f"{key}={value} "
        return f"{self.body} {attributes_str}"

    def to_string(self) -> str:
        return self.__str__()

    def to_json(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(timespec="microseconds").replace(
                "+00:00", "Z"
            ),
            "body": self.body,
            "level": self.level,
            "attributes": self.attributes,
        }


class Metric:
    timestamp: datetime
    name: str
    value: float
    attributes: Dict[str, str]

    def __init__(self, name: str, value: float, attributes: Dict[str, str]):
        self.timestamp = get_current_timestamp()
        self.name = name
        self.value = value
        self.attributes = attributes

    def to_json(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(timespec="microseconds").replace(
                "+00:00", "Z"
            ),
            "name": self.name,
            "value": self.value,
            "attributes": self.attributes,
        }
