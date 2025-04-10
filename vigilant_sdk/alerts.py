from typing import Dict
from vigilant_sdk.message import NotInitializedError
from vigilant_sdk.instance import get_global_instance
from vigilant_sdk.utils import create_alert_instance


def create_alert(title: str, attributes: Dict[str, str] = {}):
    """
    Create an alert.

    Args:
        title (str): The title of the alert.
        attributes (Dict[str, str]): The attributes to log.

    Usage:
        create_alert("This is an alert", {"user.id": "1234"})
    """
    global_instance = get_global_instance()
    if global_instance is None:
        raise NotInitializedError()

    alert = create_alert_instance(title, attributes)

    global_instance.send_alert(alert)
