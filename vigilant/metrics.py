from typing import Dict
from vigilant.message import NotInitializedError
from vigilant.instance import get_global_instance
from vigilant.types import Metric


def metric_event(name: str, value: float, attributes: Dict[str, str] = {}):
    """
    Creates a metric event.
    """
    global_instance = get_global_instance()
    if global_instance is None:
        raise NotInitializedError()

    metric = Metric(name, value, attributes)

    global_instance.send_metric(metric)
