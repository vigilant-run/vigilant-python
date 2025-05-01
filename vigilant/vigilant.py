from vigilant.log_batcher import LogBatcher
from vigilant.types import Log, Metric
from vigilant.passthrough import Passthrough
from vigilant.router import LogRouter
from vigilant.attributes import AttributeProvider
from vigilant.metric_collector import MetricCollector


class VigilantConfig:
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

    def __init__(
        self,
        name: str,
        token: str,
        endpoint: str,
        insecure: bool,
        passthrough: bool,
        autocapture: bool,
        noop: bool,
    ):
        self.name = name
        self.token = token
        self.endpoint = endpoint
        self.insecure = insecure
        self.passthrough = passthrough
        self.autocapture = autocapture
        self.noop = noop


class Vigilant:
    """
    Vigilant is a class used to send logs to Vigilant.
    It can be configured to be a noop, which will prevent it from sending any data to Vigilant.
    It requires a name and token to be configured properly.
    """

    passthrough: bool
    autocapture: bool
    noop: bool

    log_batcher: LogBatcher
    passthrough: Passthrough
    log_router: LogRouter
    attribute_provider: AttributeProvider

    def __init__(self, config: VigilantConfig):
        self.passthrough = config.passthrough
        self.autocapture = config.autocapture
        self.noop = config.noop

        self.log_batcher = create_log_batcher(config)
        self.metric_collector = create_metric_collector(config)
        self.passthrough = Passthrough()
        self.log_router = LogRouter(self.send_log)
        self.attribute_provider = AttributeProvider(config.name)

    def start(self):
        if self.noop:
            return

        self.log_batcher.start()
        self.metric_collector.start()

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

        self.metric_collector.stop()
        self.log_batcher.stop()

    def send_log(self, log: Log):
        """
        Send a log to Vigilant via the batcher.
        If passthrough, the log will be passed through to stdout or stderr.
        If noop, the log will not be sent to Vigilant.
        """
        self.attribute_provider.update_attributes(log.attributes)

        if self.passthrough:
            self.passthrough.log_passthrough(log)

        if self.noop:
            return

        self.log_batcher.add(log)

    def send_counter(self, metric: Metric):
        """
        Send a counter to Vigilant via the batcher.
        If passthrough, the counter will be passed through to stdout or stderr.
        If noop, the counter will not be sent to Vigilant.
        """
        if self.noop:
            return

        self.metric_collector.add_counter(metric)

    def send_gauge(self, metric: Metric):
        """
        Send a gauge to Vigilant via the batcher.
        If passthrough, the gauge will be passed through to stdout or stderr.
        If noop, the gauge will not be sent to Vigilant.
        """
        if self.noop:
            return

        self.metric_collector.add_gauge(metric)

    def send_histogram(self, metric: Metric):
        """
        Send a histogram to Vigilant via the batcher.
        If passthrough, the histogram will be passed through to stdout or stderr.
        If noop, the histogram will not be sent to Vigilant.
        """
        if self.noop:
            return

        self.metric_collector.add_histogram(metric)


def create_log_batcher(config: VigilantConfig) -> LogBatcher:
    return LogBatcher(
        endpoint=create_formatted_endpoint(config.endpoint, config.insecure),
        token=config.token,
        batch_interval_seconds=0.1,
        max_batch_size=1000,
    )


def create_metric_collector(config: VigilantConfig) -> MetricCollector:
    return MetricCollector(
        endpoint=create_formatted_endpoint(config.endpoint, config.insecure),
        token=config.token,
        aggregate_interval_seconds=60,
        batch_interval_seconds=0.1,
    )


def create_formatted_endpoint(endpoint: str, insecure: bool) -> str:
    if insecure:
        prefix = "http://"
    else:
        prefix = "https://"
    return prefix + endpoint + "/api/message"
