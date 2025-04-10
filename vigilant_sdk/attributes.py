import contextvars
from typing import Callable, Dict, Any, Optional, Awaitable

_STORED_ATTRIBUTES: contextvars.ContextVar[Dict[str, Any]] = contextvars.ContextVar(
    "_STORED_ATTRIBUTES", default={})


def add_attributes(attributes: Dict[str, str], callback: Optional[Callable[[], Any]] = None) -> Any:
    """
    Adds or overwrites attributes in the current context, then
    executes the callback if provided, returning the callback's result.
    """
    current_store = _STORED_ATTRIBUTES.get()
    updated_store = {**current_store, **attributes}
    token = _STORED_ATTRIBUTES.set(updated_store)

    ret = None
    try:
        if callback:
            ret = callback()
    finally:
        _STORED_ATTRIBUTES.reset(token)

    return ret


async def add_attributes_async(attributes: Dict[str, str], callback: Optional[Callable[[], Awaitable[Any]]] = None) -> Any:
    """
    Asynchronously adds or overwrites attributes in the current context,
    then executes the callback if provided, returning the callback's result.
    """
    current_store = _STORED_ATTRIBUTES.get()
    updated_store = {**current_store, **attributes}
    token = _STORED_ATTRIBUTES.set(updated_store)

    ret = None
    try:
        if callback:
            ret = await callback()
    finally:
        _STORED_ATTRIBUTES.reset(token)

    return ret


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
        current_attributes = get_attributes()
        merged_attributes = attributes.copy()
        merged_attributes.update(current_attributes)
        merged_attributes['service.name'] = self.name
        filtered_attributes = {
            k: v
            for k, v in merged_attributes.items()
            if isinstance(k, str) and isinstance(v, str)
        }
        attributes.clear()
        attributes.update(filtered_attributes)
