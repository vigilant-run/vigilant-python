from typing import TypedDict
from vigilant_sdk.batcher import Batcher
from vigilant_sdk.logs import Log


class VigilantConfig(TypedDict):
    name: str
    token: str
    endpoint: str
    insecure: bool
    passthrough: bool
    autocapture: bool
    noop: bool


class Vigilant:
    name: str
    token: str
    endpoint: str
    insecure: bool
    passthrough: bool
    autocapture: bool
    noop: bool

    log_batcher: Batcher[Log]

    def __init__(self, config: VigilantConfig):
        merged_config = merge_config(config, default_config)
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


def merge_config(config: VigilantConfig, default_config: VigilantConfig) -> VigilantConfig:
    return {**default_config, **config}


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
