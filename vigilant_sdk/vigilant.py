from typing import TypedDict
from vigilant_sdk.batcher import Batcher
from vigilant_sdk.types import Log
from vigilant_sdk.passthrough import EventPassthrough
from vigilant_sdk.router import LogRouter


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
    event_passthrough: EventPassthrough
    log_router: LogRouter

    def __init__(self, config: VigilantConfig):
        self.passthrough = config['passthrough']
        self.autocapture = config['autocapture']
        self.noop = config['noop']

        self.log_batcher = create_log_batcher(config)
        self.event_passthrough = EventPassthrough()
        self.log_router = LogRouter(self.send_log)

    def start(self):
        if self.noop:
            return
        self.log_batcher.start()
        if self.autocapture:
            self.log_router.enable()

    def shutdown(self):
        """
        Manually shutdown the batcher synchronously. Blocks until complete.
        """
        if self.noop:
            return
        if self.autocapture:
            self.log_router.disable()
        self.log_batcher.shutdown()

    def send_log(self, log: Log):
        """
        Send a log to Vigilant via the batcher.
        If passthrough, the log will be passed through to stdout or stderr.
        If noop, the log will not be sent to Vigilant.
        """
        if self.passthrough:
            self.event_passthrough.log_passthrough(log)
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
