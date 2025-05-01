import atexit
import sys
import threading
from typing import Optional
from vigilant.config import VigilantUserConfig
from vigilant.message import UnexpectedFailureError, AlreadyInitializedError
from vigilant.vigilant import Vigilant, VigilantConfig

_global_instance: Optional[Vigilant] = None
_shutdown_registered: bool = False
_global_instance_lock = threading.Lock()


def init_vigilant(user_config: Optional[VigilantUserConfig] = None):
    """
    Initialize the global instance with the provided configuration.
    Starts background thread for sending logs.
    Automatically shuts down the global instance when the process is terminated.
    """
    global _global_instance, _shutdown_registered
    with _global_instance_lock:
        if _global_instance:
            raise AlreadyInitializedError()

        final_config = _merge_config(user_config, _default_config)
        instance = Vigilant(final_config)
        temp_instance = None

        try:
            instance.start()
            temp_instance = instance
            if not _shutdown_registered:
                _add_shutdown_listeners()
                _shutdown_registered = True
        except Exception as e:
            raise UnexpectedFailureError(
                f"Failed to initialize Vigilant: {e}") from e
        finally:
            _global_instance = temp_instance


def shutdown_vigilant():
    """
    Manually shutdown the global instance synchronously.
    Blocks until shutdown is complete.
    Removes the exit listener if called manually.
    """
    instance_to_shutdown = None
    registered = False
    global _global_instance, _shutdown_registered

    with _global_instance_lock:
        instance_to_shutdown = _global_instance
        registered = _shutdown_registered
        _global_instance = None
        _shutdown_registered = False

    if registered:
        _remove_shutdown_listeners()

    if instance_to_shutdown:
        instance_to_shutdown.shutdown()


def get_global_instance():
    global _global_instance
    return _global_instance


def _shutdown_sync():
    """Synchronous wrapper for shutdown, suitable for atexit."""
    instance_to_shutdown = None
    global _global_instance

    with _global_instance_lock:
        instance_to_shutdown = _global_instance

    if instance_to_shutdown:
        if instance_to_shutdown.noop:
            return
        try:
            instance_to_shutdown.shutdown()
        except Exception as e:
            print(
                f"Error during Vigilant atexit shutdown: {e}", file=sys.stderr)


def _add_shutdown_listeners():
    """Registers the synchronous shutdown handler to be called on program exit."""
    atexit.register(_shutdown_sync)


def _remove_shutdown_listeners():
    """Unregisters the shutdown handler."""
    try:
        atexit.unregister(_shutdown_sync)
    except ValueError:
        pass
    except Exception as e:
        print(
            f"Error unregistering Vigilant shutdown handler: {e}", file=sys.stderr)


def _merge_config(user_config: Optional[VigilantUserConfig], default_config: VigilantConfig) -> VigilantConfig:
    if user_config is None:
        return default_config

    return VigilantConfig(
        name=user_config.name,
        token=user_config.token,
        endpoint=user_config.endpoint if user_config.endpoint is not None else default_config.endpoint,
        insecure=user_config.insecure if user_config.insecure is not None else default_config.insecure,
        passthrough=user_config.passthrough if user_config.passthrough is not None else default_config.passthrough,
        autocapture=user_config.autocapture if user_config.autocapture is not None else default_config.autocapture,
        noop=user_config.noop if user_config.noop is not None else default_config.noop,
    )


_default_config: VigilantConfig = VigilantConfig(
    name="backend",
    token="generated-token-here",
    endpoint="ingress.vigilant.run",
    insecure=False,
    passthrough=True,
    autocapture=True,
    noop=False,
)
