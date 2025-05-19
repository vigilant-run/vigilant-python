from enum import Enum
from typing import Dict, List, Any
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


class CounterEvent:
    name: str
    value: float
    tags: Dict[str, str]

    def __init__(self, name: str, value: float, tags: Dict[str, str]):
        self.name = name
        self.tags = tags
        self.value = value


class GaugeMode(str, Enum):
    INC = "inc"
    DEC = "dec"
    SET = "set"


class GaugeEvent:
    name: str
    value: float
    mode: GaugeMode
    tags: Dict[str, str]

    def __init__(self, name: str, value: float, mode: GaugeMode, tags: Dict[str, str]):
        self.name = name
        self.tags = tags
        self.value = value
        self.mode = mode


class HistogramEvent:
    name: str
    tags: Dict[str, str]
    value: float

    def __init__(self, name: str, value: float, tags: Dict[str, str]):
        self.name = name
        self.tags = tags
        self.value = value


class CounterMessage:
    timestamp: datetime
    metric_name: str
    value: float
    tags: Dict[str, str]

    def __init__(
        self, timestamp: datetime, name: str, value: float, tags: Dict[str, str]
    ):
        self.timestamp = timestamp
        self.name = name
        self.value = value
        self.tags = tags

    def to_json(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(timespec="microseconds").replace(
                "+00:00", "Z"
            ),
            "metric_name": self.name,
            "value": self.value,
            "tags": self.tags,
        }


class GaugeMessage:
    timestamp: datetime
    metric_name: str
    value: float
    tags: Dict[str, str]

    def __init__(
        self, timestamp: datetime, name: str, value: float, tags: Dict[str, str]
    ):
        self.timestamp = timestamp
        self.name = name
        self.value = value
        self.tags = tags

    def to_json(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(timespec="microseconds").replace(
                "+00:00", "Z"
            ),
            "metric_name": self.name,
            "value": self.value,
            "tags": self.tags,
        }


class HistogramMessage:
    timestamp: datetime
    metric_name: str
    values: List[float]
    tags: Dict[str, str]

    def __init__(
        self, timestamp: datetime, name: str, values: List[float], tags: Dict[str, str]
    ):
        self.timestamp = timestamp
        self.name = name
        self.values = values
        self.tags = tags

    def to_json(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(timespec="microseconds").replace(
                "+00:00", "Z"
            ),
            "metric_name": self.name,
            "values": self.values,
            "tags": self.tags,
        }


class AggregatedMetrics:
    counter_metrics: List[CounterMessage]
    gauge_metrics: List[GaugeMessage]
    histogram_metrics: List[HistogramMessage]

    def __init__(self):
        self.counter_metrics = []
        self.gauge_metrics = []
        self.histogram_metrics = []

    def to_json(self) -> Dict[str, Any]:
        return {
            "counter_metrics": [metric.to_json() for metric in self.counter_metrics],
            "gauge_metrics": [metric.to_json() for metric in self.gauge_metrics],
            "histogram_metrics": [
                metric.to_json() for metric in self.histogram_metrics
            ],
        }


class CounterSeries:
    name: str
    tags: Dict[str, str]
    value: float

    def __init__(self, name: str, tags: Dict[str, str], value: float):
        self.name = name
        self.tags = tags
        self.value = value

    def to_json(self) -> Dict[str, Any]:
        return {"name": self.name, "tags": self.tags, "value": self.value}


class GaugeSeries:
    name: str
    tags: Dict[str, str]
    value: float

    def __init__(self, name: str, tags: Dict[str, str], value: float):
        self.name = name
        self.tags = tags
        self.value = value

    def to_json(self) -> Dict[str, Any]:
        return {"name": self.name, "tags": self.tags, "value": self.value}


class HistogramSeries:
    name: str
    tags: Dict[str, str]
    values: List[float]

    def __init__(self, name: str, tags: Dict[str, str], values: List[float]):
        self.name = name
        self.tags = tags
        self.values = values

    def to_json(self) -> Dict[str, Any]:
        return {"name": self.name, "tags": self.tags, "values": self.values}
