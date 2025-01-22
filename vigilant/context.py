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


def remove_attributes(keys: list, callback: Optional[Callable[[], None]] = None) -> None:
    """
    Removes specific attributes from the current context, then
    executes the callback if provided.
    """
    current_store = _STORED_ATTRIBUTES.get()
    updated_store = {k: v for k, v in current_store.items() if k not in keys}
    token = _STORED_ATTRIBUTES.set(updated_store)

    try:
        if callback:
            callback()
    finally:
        _STORED_ATTRIBUTES.reset(token)


def clear_attributes(callback: Optional[Callable[[], None]] = None) -> None:
    """
    Clears all attributes in the current context, then executes the callback if provided.
    """
    token = _STORED_ATTRIBUTES.set({})
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
