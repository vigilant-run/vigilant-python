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
