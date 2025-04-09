from enum import Enum
from typing import TypedDict, Dict


class LogLevel(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    DEBUG = "DEBUG"
    TRACE = "TRACE"


class Log(TypedDict):
    timestamp: str
    body: str
    level: LogLevel
    attributes: Dict[str, str]

    def __str__(self) -> str:
        attributes_str = ""
        for key, value in self.attributes.items():
            attributes_str += f"{key}={value} "
        return f"{self.body} {attributes_str}"

    def to_string(self) -> str:
        return self.__str__()
