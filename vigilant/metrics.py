from typing import Dict
from vigilant.message import NotInitializedError
from vigilant.instance import get_global_instance
from vigilant.types import CounterEvent, GaugeEvent, HistogramEvent, GaugeMode


def metric_counter(name: str, value: float, tags: Dict[str, str] = {}):
    """
    Creates a counter metric.

    Args:
        name (str): The name of the metric.
        value (float): The value of the metric.
        tags (Dict[str, str]): The tags of the metric.
    """
    global_instance = get_global_instance()
    if global_instance is None:
        raise NotInitializedError()

    metric = CounterEvent(name, value, tags)

    global_instance.send_counter(metric)


def metric_gauge(name: str, value: float, mode: GaugeMode = GaugeMode.SET, tags: Dict[str, str] = {}):
    """
    Creates a gauge metric.

    Args:
        name (str): The name of the metric.
        value (float): The value of the metric.
        tags (Dict[str, str]): The tags of the metric.
    """
    global_instance = get_global_instance()
    if global_instance is None:
        raise NotInitializedError()

    metric = GaugeEvent(name, value, mode, tags)

    global_instance.send_gauge(metric)


def metric_histogram(name: str, value: float, tags: Dict[str, str] = {}):
    """
    Creates a histogram metric.

    Args:
        name (str): The name of the metric.
        value (float): The value of the metric.
        tags (Dict[str, str]): The tags of the metric.
    """
    global_instance = get_global_instance()
    if global_instance is None:
        raise NotInitializedError()

    metric = HistogramEvent(name, value, tags)

    global_instance.send_histogram(metric)
