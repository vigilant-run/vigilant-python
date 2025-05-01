from typing import Dict, List, Optional
import time
import threading
import queue
from datetime import datetime, timedelta, timezone
from vigilant.types import Metric, AggregatedMetrics, CounterMessage, GaugeMessage, HistogramMessage, CapturedMetrics, CapturedCounter, CapturedGauge, CapturedHistogram
from vigilant.metric_sender import MetricSender


class MetricCollector:
    def __init__(self, endpoint: str, token: str, aggregate_interval_seconds: int, batch_interval_seconds: float):
        self.endpoint = endpoint
        self.token = token
        self.aggregate_interval = timedelta(seconds=aggregate_interval_seconds)
        self.captured_buckets: Dict[datetime, CapturedMetrics] = {}

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

        processor = threading.Thread(
            target=self._process_events, daemon=True)
        self.worker_threads.append(processor)
        processor.start()

        self.ticker_thread = threading.Thread(
            target=self._run_ticker, daemon=True)
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

    def add_counter(self, metric: Metric):
        """Adds a counter metric to the collector's queue."""
        if self.stop_event.is_set():
            return
        self._put_event(self.counter_events, metric)

    def add_gauge(self, metric: Metric):
        """Adds a gauge metric to the collector's queue."""
        if self.stop_event.is_set():
            return
        self._put_event(self.gauge_events, metric)

    def add_histogram(self, metric: Metric):
        """Adds a histogram metric to the collector's queue."""
        if self.stop_event.is_set():
            return
        self._put_event(self.histogram_events, metric)

    def _run_ticker(self):
        """Runs the ticker loop."""
        try:
            while not self.stop_event.is_set():
                now = datetime.now(timezone.utc)
                current_interval_start = _truncate_datetime(
                    now, self.aggregate_interval)
                next_interval_start = current_interval_start + self.aggregate_interval
                first_trigger_time = next_interval_start + timedelta(seconds=1)

                wait_duration_seconds = (
                    first_trigger_time - now).total_seconds()
                wait_duration_seconds = max(0, wait_duration_seconds)

                self.ticker_timer = threading.Timer(
                    wait_duration_seconds, self._tick_action, args=[current_interval_start])
                self.ticker_timer.start()
                self.ticker_timer.join()

                if self.stop_event.is_set():
                    break

                interval_seconds = self.aggregate_interval.total_seconds()
                while not self.stop_event.wait(interval_seconds):
                    if self.stop_event.is_set():
                        break
                    last_interval_start = _truncate_datetime(
                        datetime.now(timezone.utc) - self.aggregate_interval, self.aggregate_interval)
                    self._tick_action(last_interval_start)

        except Exception:
            pass
        finally:
            if self.ticker_timer and self.ticker_timer.is_alive():
                self.ticker_timer.cancel()

    def _tick_action(self, interval_to_process: datetime):
        """Sends metrics for the completed interval."""
        if self.stop_event.is_set():
            return
        print("MetricCollector: _tick_action: sending metrics for interval",
              interval_to_process)
        self._send_metrics_for_interval(interval_to_process)

    def _process_events(self):
        """Reads metric events from queues and updates the buckets."""
        active = True
        while active:
            try:
                try:
                    event = self.counter_events.get(timeout=0.1)
                    print("MetricCollector: _process_events: event",
                          event)
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
                    if self.counter_events.empty() and self.gauge_events.empty() and self.histogram_events.empty():
                        active = False

            except Exception as e:
                print("MetricCollector: _process_events: error",
                      e)
                time.sleep(0.5)

    def _put_event(self, q: queue.Queue, event: Metric):
        """Helper to put event onto a queue if not stopped."""
        if self.stop_event.is_set():
            return
        try:
            q.put_nowait(event)
        except queue.Full:
            pass

    def _get_bucket(self, timestamp: datetime) -> CapturedMetrics:
        """Gets or creates the bucket for the given timestamp, protected by lock."""
        bucket_time = _truncate_datetime(timestamp, self.aggregate_interval)
        with self.lock:
            bucket = self.captured_buckets.get(bucket_time)
            if bucket is None:
                bucket = CapturedMetrics()
                self.captured_buckets[bucket_time] = bucket
            return bucket

    def _process_counter_event(self, event: Metric):
        """Processes a queued counter event."""
        bucket = self._get_bucket(event.timestamp)
        identifier = _generate_metric_identifier(event.name, event.tags)

        print("MetricCollector: _process_counter_event: bucket",
              bucket)
        print("MetricCollector: _process_counter_event: identifier",
              identifier)

        counter = bucket.counters.get(identifier)
        if counter:
            counter.value += event.value
        else:
            bucket.counters[identifier] = CapturedCounter(
                name=event.name,
                tags=event.tags,
                value=event.value,
            )

    def _process_gauge_event(self, event: Metric):
        """Processes a queued gauge event."""
        bucket = self._get_bucket(event.timestamp)
        identifier = _generate_metric_identifier(event.name, event.tags)

        gauge = bucket.gauges.get(identifier)
        if gauge:
            gauge.value = event.value
        else:
            bucket.gauges[identifier] = CapturedGauge(
                name=event.name,
                tags=event.tags,
                value=event.value,
            )

    def _process_histogram_event(self, event: Metric):
        """Processes a queued histogram event."""
        bucket = self._get_bucket(event.timestamp)
        identifier = _generate_metric_identifier(event.name, event.tags)

        histogram = bucket.histograms.get(identifier)
        if histogram:
            histogram.values.append(event.value)
        else:
            bucket.histograms[identifier] = CapturedHistogram(
                name=event.name,
                tags=event.tags,
                values=[event.value],
            )

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

    def _send_metrics_for_interval(self, interval_start: datetime):
        """Aggregates, sends metrics for the interval, and cleans up."""
        metrics_to_send: Optional[AggregatedMetrics] = None
        bucket_to_send: Optional[CapturedMetrics] = None

        with self.lock:
            bucket = self.captured_buckets.get(interval_start)
            if bucket and (bucket.counters or bucket.gauges or bucket.histograms):
                bucket_to_send = bucket
                del self.captured_buckets[interval_start]

        if bucket_to_send:
            metrics_to_send = self._aggregate_captured_metrics(
                interval_start, bucket_to_send)

        if metrics_to_send and (len(metrics_to_send.counter_metrics) > 0 or len(metrics_to_send.gauge_metrics) > 0 or len(metrics_to_send.histogram_metrics) > 0):
            self.metric_sender.add(metrics_to_send)

        self._cleanup_old_buckets(interval_start)

    def _cleanup_old_buckets(self, current_interval_just_processed: datetime):
        """Removes buckets older than the previous interval."""
        cleanup_threshold = current_interval_just_processed - self.aggregate_interval
        to_delete = []
        with self.lock:
            for ts in self.captured_buckets.keys():
                if ts < cleanup_threshold:
                    to_delete.append(ts)

            if to_delete:
                for ts in to_delete:
                    del self.captured_buckets[ts]

    def _send_after_shutdown(self):
        """Sends all remaining metrics currently held in buckets."""
        buckets_to_send: Dict[datetime, CapturedMetrics] = {}

        with self.lock:
            buckets_to_send = self.captured_buckets
            self.captured_buckets = {}

        timestamps_sorted = sorted(buckets_to_send.keys())

        for timestamp in timestamps_sorted:
            bucket = buckets_to_send[timestamp]
            if bucket and (bucket.counters or bucket.gauges or bucket.histograms):
                aggregated = self._aggregate_captured_metrics(
                    timestamp, bucket)
                counter_count = len(aggregated.counter_metrics)
                gauge_count = len(aggregated.gauge_metrics)
                histogram_count = len(aggregated.histogram_metrics)
                if counter_count > 0 or gauge_count > 0 or histogram_count > 0:
                    self.metric_sender.add(aggregated)

    def _aggregate_captured_metrics(self, timestamp: datetime, captured: CapturedMetrics) -> AggregatedMetrics:
        """Transforms captured metrics into the format expected by the sender."""
        aggregated = AggregatedMetrics()

        for counter in captured.counters.values():
            message = CounterMessage(
                timestamp,
                counter.name,
                counter.value,
                counter.tags,
            )
            aggregated.counter_metrics.append(message)

        for gauge in captured.gauges.values():
            message = GaugeMessage(
                timestamp,
                gauge.name,
                gauge.value,
                gauge.tags,
            )
            aggregated.gauge_metrics.append(message)

        for histogram in captured.histograms.values():
            message = HistogramMessage(
                timestamp,
                histogram.name,
                histogram.values,
                histogram.tags,
            )
            aggregated.histogram_metrics.append(message)

        return aggregated


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
    sorted_tags = sorted(tags.items())
    tag_string = "_".join(f"{k}_{v}" for k, v in sorted_tags)
    return f"{name}_{tag_string}"
