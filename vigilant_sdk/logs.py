from enum import Enum
from typing import TypedDict, Dict


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
