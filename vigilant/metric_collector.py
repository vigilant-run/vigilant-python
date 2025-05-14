from typing import Dict, List, Optional
import time
import threading
import queue
from datetime import datetime, timedelta, timezone
from vigilant.types import (
    AggregatedMetrics,
    CounterMessage,
    GaugeMessage,
    HistogramMessage,
    CounterEvent,
    GaugeEvent,
    HistogramEvent,
    CounterSeries,
    GaugeSeries,
    HistogramSeries,
    GaugeMode,
)
from vigilant.metric_sender import MetricSender


class MetricCollector:
    def __init__(
        self,
        endpoint: str,
        token: str,
        aggregate_interval_seconds: int,
        batch_interval_seconds: float,
    ):
        self.endpoint = endpoint
        self.token = token
        self.aggregate_interval = timedelta(seconds=aggregate_interval_seconds)

        self.counter_series: Dict[str, CounterSeries] = {}
        self.gauge_series: Dict[str, GaugeSeries] = {}
        self.histogram_series: Dict[str, HistogramSeries] = {}

        self.counter_events = queue.Queue(maxsize=1_000)
        self.gauge_events = queue.Queue(maxsize=1_000)
        self.histogram_events = queue.Queue(maxsize=1_000)

        self.lock = threading.Lock()

        self.stop_event = threading.Event()
        self.worker_threads: List[threading.Thread] = []
        self.ticker_thread: Optional[threading.Thread] = None
        self.ticker_timer: Optional[threading.Timer] = None

        self.metric_sender = MetricSender(
            endpoint=endpoint,
            token=token,
            batch_interval_seconds=batch_interval_seconds,
        )

    def start(self):
        """Starts the collector."""
        if self.worker_threads or self.ticker_thread:
            return

        self.stop_event.clear()

        self.metric_sender.start()

        processor = threading.Thread(target=self._process_events, daemon=True)
        self.worker_threads.append(processor)
        processor.start()

        self.ticker_thread = threading.Thread(target=self._run_ticker, daemon=True)
        self.ticker_thread.start()

    def stop(self):
        """Stops the collector."""
        if self.stop_event.is_set():
            return

        self.stop_event.set()

        if self.ticker_timer and self.ticker_timer.is_alive():
            self.ticker_timer.cancel()

        self.counter_events.put(None)
        self.gauge_events.put(None)
        self.histogram_events.put(None)

        if self.ticker_thread:
            self.ticker_thread.join(timeout=5)

        for thread in self.worker_threads:
            thread.join(timeout=5)

        self.worker_threads = []
        self.ticker_thread = None

        self._process_after_shutdown()
        self._send_after_shutdown()

        self.metric_sender.stop()

    def add_counter(self, event: CounterEvent):
        """Adds a counter metric to the collector's queue."""
        if self.stop_event.is_set():
            return
        if self.counter_events.full():
            return
        self.counter_events.put(event)

    def add_gauge(self, event: GaugeEvent):
        """Adds a gauge metric to the collector's queue."""
        if self.stop_event.is_set():
            return
        if self.gauge_events.full():
            return
        self.gauge_events.put(event)

    def add_histogram(self, event: HistogramEvent):
        """Adds a histogram metric to the collector's queue."""
        if self.stop_event.is_set():
            return
        if self.histogram_events.full():
            return
        self.histogram_events.put(event)

    def _run_ticker(self):
        """Runs the ticker loop."""
        try:
            while not self.stop_event.is_set():
                now = datetime.now(timezone.utc)
                current_interval_start = _truncate_datetime(
                    now, self.aggregate_interval
                )
                next_start = current_interval_start + self.aggregate_interval
                first_time = next_start + timedelta(milliseconds=50)

                wait_duration_seconds = (first_time - now).total_seconds()
                wait_duration_seconds = max(0, wait_duration_seconds)

                self.ticker_timer = threading.Timer(
                    wait_duration_seconds,
                    self._tick_action,
                    args=[current_interval_start],
                )
                self.ticker_timer.start()
                self.ticker_timer.join()

                if self.stop_event.is_set():
                    break

                interval_seconds = self.aggregate_interval.total_seconds()
                while not self.stop_event.wait(interval_seconds):
                    if self.stop_event.is_set():
                        break
                    last_interval_start = _truncate_datetime(
                        datetime.now(timezone.utc) - self.aggregate_interval,
                        self.aggregate_interval,
                    )
                    self._tick_action(last_interval_start)

        except Exception as e:
            pass
        finally:
            if self.ticker_timer and self.ticker_timer.is_alive():
                self.ticker_timer.cancel()

    def _tick_action(self, timestamp: datetime):
        """Sends metrics for the completed interval."""
        if self.stop_event.is_set():
            return
        self._send_metrics_for_interval(timestamp)

    def _process_events(self):
        """Reads metric events from queues and updates the buckets."""
        active = True
        while active:
            try:
                try:
                    event = self.counter_events.get(timeout=0.1)
                    if event is None:
                        active = False
                        continue
                    self._process_counter_event(event)
                    self.counter_events.task_done()
                    continue
                except queue.Empty:
                    pass

                try:
                    event = self.gauge_events.get(timeout=0.1)
                    if event is None:
                        active = False
                        continue
                    self._process_gauge_event(event)
                    self.gauge_events.task_done()
                    continue
                except queue.Empty:
                    pass

                try:
                    event = self.histogram_events.get(timeout=0.1)
                    if event is None:
                        active = False
                        continue
                    self._process_histogram_event(event)
                    self.histogram_events.task_done()
                    continue
                except queue.Empty:
                    pass

                if self.stop_event.is_set():
                    if (
                        self.counter_events.empty()
                        and self.gauge_events.empty()
                        and self.histogram_events.empty()
                    ):
                        active = False

            except Exception:
                time.sleep(0.5)

    def _process_counter_event(self, event: CounterEvent):
        """Processes a queued counter event."""
        identifier = _generate_metric_identifier(event.name, event.tags)

        with self.lock:
            series = self.counter_series.get(identifier)
            if series:
                series.value += event.value
            else:
                new_series = CounterSeries(
                    name=event.name,
                    tags=event.tags,
                    value=0,
                )
                new_series.value = event.value
                self.counter_series[identifier] = new_series

    def _process_gauge_event(self, event: GaugeEvent):
        """Processes a queued gauge event."""
        identifier = _generate_metric_identifier(event.name, event.tags)

        with self.lock:
            series = self.gauge_series.get(identifier)
            if series:
                if event.mode == GaugeMode.SET:
                    series.value = event.value
                elif event.mode == GaugeMode.INC:
                    series.value += event.value
                elif event.mode == GaugeMode.DEC:
                    series.value -= event.value
            else:
                new_series = GaugeSeries(
                    name=event.name,
                    tags=event.tags,
                    value=0,
                )
                if event.mode == GaugeMode.SET:
                    new_series.value = event.value
                elif event.mode == GaugeMode.INC:
                    new_series.value += event.value
                elif event.mode == GaugeMode.DEC:
                    new_series.value -= event.value
                self.gauge_series[identifier] = new_series

    def _process_histogram_event(self, event: HistogramEvent):
        """Processes a queued histogram event."""
        identifier = _generate_metric_identifier(event.name, event.tags)

        with self.lock:
            series = self.histogram_series.get(identifier)
            if series:
                series.values.append(event.value)
            else:
                new_series = HistogramSeries(
                    name=event.name,
                    tags=event.tags,
                    values=[],
                )
                new_series.values.append(event.value)
                self.histogram_series[identifier] = new_series

    def _process_after_shutdown(self):
        """Drains event queues after worker threads have stopped."""
        while True:
            try:
                event = self.counter_events.get_nowait()
                if event is None:
                    continue
                self._process_counter_event(event)
                self.counter_events.task_done()
            except queue.Empty:
                break
            except Exception:
                pass

        while True:
            try:
                event = self.gauge_events.get_nowait()
                if event is None:
                    continue
                self._process_gauge_event(event)
                self.gauge_events.task_done()
            except queue.Empty:
                break
            except Exception:
                pass

        while True:
            try:
                event = self.histogram_events.get_nowait()
                if event is None:
                    continue
                self._process_histogram_event(event)
                self.histogram_events.task_done()
            except queue.Empty:
                break
            except Exception:
                pass

    def _send_metrics_for_interval(self, timestamp: datetime):
        """Aggregates, sends metrics for the interval, and cleans up."""
        aggregated: Optional[AggregatedMetrics] = None

        with self.lock:
            aggregated = self._aggregate_series_with_lock(timestamp)
            self._reset_series()

        if aggregated:
            self.metric_sender.add(aggregated)

    def _send_after_shutdown(self):
        """Sends all remaining metrics currently held in buckets."""
        aggregated: Optional[AggregatedMetrics] = None

        with self.lock:
            now = datetime.now(timezone.utc)
            timestamp = _truncate_datetime(now, self.aggregate_interval)
            aggregated = self._aggregate_series_with_lock(timestamp)
            self._reset_series()

        if aggregated:
            self.metric_sender.add(aggregated)

    def _aggregate_series_with_lock(self, timestamp: datetime) -> AggregatedMetrics:
        """Transforms captured metrics into the format expected by the sender. This expects the lock to be held."""
        aggregated = AggregatedMetrics()

        for counter in self.counter_series.values():
            message = CounterMessage(
                timestamp,
                counter.name,
                counter.value,
                counter.tags,
            )
            aggregated.counter_metrics.append(message)

        for gauge in self.gauge_series.values():
            message = GaugeMessage(
                timestamp,
                gauge.name,
                gauge.value,
                gauge.tags,
            )
            aggregated.gauge_metrics.append(message)

        for histogram in self.histogram_series.values():
            message = HistogramMessage(
                timestamp,
                histogram.name,
                histogram.values,
                histogram.tags,
            )
            aggregated.histogram_metrics.append(message)

        return aggregated

    def _reset_series(self):
        """Resets the series for the current interval."""
        for series in self.counter_series.values():
            series.value = 0
        for series in self.histogram_series.values():
            series.values = []


def _truncate_datetime(dt: datetime, interval: timedelta) -> datetime:
    """Truncates a datetime object to the beginning of its interval."""
    if interval.total_seconds() <= 0:
        return dt.replace(microsecond=0)

    interval_seconds = int(interval.total_seconds())
    timestamp = int(dt.timestamp())
    truncated_timestamp = timestamp - (timestamp % interval_seconds)
    return datetime.fromtimestamp(truncated_timestamp, tz=timezone.utc)


def _generate_metric_identifier(name: str, tags: Optional[Dict[str, str]]) -> str:
    """Generates a unique string identifier for a metric based on name and tags."""
    if not tags:
        return name
    sorted_tags = sorted(tags.keys())
    tag_string = "_".join(f"{k}_{tags[k]}" for k in sorted_tags)
    return f"{name}_{tag_string}"
