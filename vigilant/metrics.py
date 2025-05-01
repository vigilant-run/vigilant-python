from typing import Dict
from vigilant.message import NotInitializedError
from vigilant.instance import get_global_instance
from vigilant.utils import get_current_timestamp
from vigilant.types import Metric


def counter(name: str, value: float, tags: Dict[str, str] = {}):
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

    metric = Metric(name, value, tags)
    global_instance.send_counter(metric)


def gauge(name: str, value: float, tags: Dict[str, str] = {}):
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

    metric = Metric(name, value, tags)
    global_instance.send_gauge(metric)


def histogram(name: str, value: float, tags: Dict[str, str] = {}):
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

    metric = Metric(name, value, tags)

    global_instance.send_histogram(metric)
