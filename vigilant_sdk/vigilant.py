from typing import TypedDict
from vigilant_sdk.batcher import Batcher
from vigilant_sdk.types import Log


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
    passthrough: bool
    autocapture: bool
    noop: bool

    log_batcher: Batcher[Log]

    def __init__(self, config: VigilantConfig):
        self.passthrough = config['passthrough']
        self.autocapture = config['autocapture']
        self.noop = config['noop']

        self.log_batcher = create_log_batcher(config)

    def start(self):
        if self.noop:
            return
        self.log_batcher.start()

    def shutdown(self):
        """
        Manually shutdown the batcher synchronously. Blocks until complete.
        """
        if self.noop:
            return
        self.log_batcher.shutdown()

    def send_log(self, log: Log):
        if self.noop:
            return
        self.log_batcher.add(log)


def create_log_batcher(config: VigilantConfig) -> Batcher[Log]:
    return Batcher(
        endpoint=create_formatted_endpoint(
            config['endpoint'], config['insecure']),
        token=config['token'],
        type_name="logs",
        key="logs",
        batch_interval_seconds=0.1,
        max_batch_size=1000,
    )


def create_formatted_endpoint(endpoint: str, insecure: bool) -> str:
    if insecure:
        prefix = 'http://'
    else:
        prefix = 'https://'
    return prefix + endpoint + '/api/message'
