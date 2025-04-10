import atexit
from typing import TypedDict, Optional
from vigilant_sdk.batcher import Batcher
from vigilant_sdk.logs import Log
from vigilant_sdk.config import VigilantUserConfig


class VigilantConfig(TypedDict):
    """
    VigilantConfig is a class used to configure the Vigilant SDK.
    It requires a name and token to be configured properly.
    """
    name: str
    token: str
    endpoint: str
    insecure: bool
    passthrough: bool
    autocapture: bool
    noop: bool


class Vigilant:
    """
    Vigilant is a class used to send logs, alerts, and metrics to Vigilant.
    It can be configured to be a noop, which will prevent it from sending any data to Vigilant.
    It requires a name and token to be configured properly.
    """
    name: str
    token: str
    endpoint: str
    insecure: bool
    passthrough: bool
    autocapture: bool
    noop: bool

    log_batcher: Batcher[Log]

    def __init__(self, user_config: VigilantUserConfig):
        merged_config = merge_config(user_config, default_config)
        self.name = merged_config.name
        self.token = merged_config.token
        self.endpoint = create_formatted_endpoint(
            merged_config.endpoint, merged_config.insecure)
        self.passthrough = merged_config.passthrough
        self.autocapture = merged_config.autocapture
        self.noop = merged_config.noop

    def start(self):
        pass

    def shutdown(self):
        pass

    def send_log(self):
        pass


def merge_config(user_config: VigilantUserConfig, default_config: VigilantConfig) -> VigilantConfig:
    return {**default_config, **user_config}


def create_log_batcher(config: VigilantConfig) -> Batcher[Log]:
    return Batcher(
        endpoint=config.endpoint,
        token=config.token,
        type_name="log",
        key="log",
        batch_interval_seconds=0.1,
        max_batch_size=1000,
    )


def create_formatted_endpoint(endpoint: str, insecure: bool) -> str:
    if insecure:
        prefix = 'http://'
    else:
        prefix = 'https://'
    return prefix + endpoint + '/api/message'


default_config: VigilantConfig = {
    "name": "backend",
    "token": "generated-token-here",
    "endpoint": "ingress.vigilant.run",
    "insecure": False,
    "passthrough": False,
    "autocapture": True,
    "noop": False,
}

_global_instance: Optional[Vigilant] = None


def init_vigilant(config: VigilantConfig):
    """
    Initialize the global instance with the provided configuration.
    Automatically shuts down the global instance when the process is terminated.
    """
    global _global_instance
    merged_config = merge_config(config, default_config)
    _global_instance = Vigilant(merged_config)
    _global_instance.start()
    _add_shutdown_listeners()


def shutdown_vigilant():
    """
    Manually shutdown the global instance and remove the exit listener.
    """
    global _global_instance
    _remove_shutdown_listeners()  # Remove listener first
    if _global_instance:
        _global_instance.shutdown()
        _global_instance = None


def _add_shutdown_listeners():
    """Registers the shutdown handler to be called on program exit."""
    atexit.register(shutdown_vigilant)


def _remove_shutdown_listeners():
    """Unregisters the shutdown handler."""
    try:
        atexit.unregister(shutdown_vigilant)
    except ValueError:
        pass
