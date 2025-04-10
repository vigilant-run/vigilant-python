import contextvars
from typing import Callable, Dict, Any, Optional

_STORED_ATTRIBUTES: contextvars.ContextVar[Dict[str, Any]] = contextvars.ContextVar(
    "_STORED_ATTRIBUTES", default={})


def add_attributes(attributes: Dict[str, str], callback: Optional[Callable[[], None]] = None) -> None:
    """
    Adds or overwrites attributes in the current context, then
    executes the callback if provided.
    """
    current_store = _STORED_ATTRIBUTES.get()
    updated_store = {**current_store, **attributes}
    token = _STORED_ATTRIBUTES.set(updated_store)

    try:
        if callback:
            callback()
    finally:
        _STORED_ATTRIBUTES.reset(token)


def get_attributes() -> Dict[str, str]:
    """
    Returns the attributes currently stored in the context.
    """
    return _STORED_ATTRIBUTES.get()


class AttributeProvider:
    """
    AttributeProvider is a class that provides attributes to the current context.
    """
    name: str

    def __init__(self, name: str):
        self.name = name

    def update_attributes(self, attributes: Dict[str, str]):
        current_store = _STORED_ATTRIBUTES.get()
        attributes.update(current_store)
        attributes['service.name'] = self.name
