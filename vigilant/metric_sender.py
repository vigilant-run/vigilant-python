import threading
import queue
import time
import requests
from typing import Optional, Dict, Any
from vigilant.types import AggregatedMetrics
from vigilant.message import (
    VigilantError,
    BatcherInvalidTokenError,
    BatcherInternalServerError,
)


class MetricSender:
    """
    A class used to batch and send metric batches synchronously in a background thread
    using the requests library.
    """

    def __init__(
        self,
        endpoint: str,
        token: str,
        batch_interval_seconds: float,
    ):
        self.endpoint: str = endpoint
        self.token: str = token
        self.batch_interval_seconds: float = batch_interval_seconds

        self._thread_safe_queue: queue.Queue[Optional[AggregatedMetrics]] = queue.Queue(
            maxsize=1_000
        )
        self._background_thread: Optional[threading.Thread] = None
        self._stop_event: threading.Event = threading.Event()
        self._session: Optional[requests.Session] = None

    def add(self, item: AggregatedMetrics) -> None:
        """Adds an item to the thread-safe queue for processing by the background thread."""
        if self._stop_event.is_set() or self._background_thread is None:
            return
        try:
            self._thread_safe_queue.put_nowait(item)
        except queue.Full:
            pass

    def start(self) -> None:
        """Starts the background thread."""
        if self._background_thread is not None:
            return

        self._stop_event.clear()
        self._session = requests.Session()
        self._session.headers.update({"Content-Type": "application/json"})

        self._background_thread = threading.Thread(
            target=self._run_background_loop, daemon=True
        )
        self._background_thread.start()

    def stop(self) -> None:
        """Shuts down the batcher gracefully. Blocks until finished."""
        if self._background_thread is None or not self._background_thread.is_alive():
            return

        if self._stop_event.is_set():
            return

        self._stop_event.set()

        try:
            self._thread_safe_queue.put_nowait(None)
        except queue.Full:
            pass

        if self._background_thread != threading.current_thread():
            self._background_thread.join(timeout=10)
            if self._background_thread.is_alive():
                pass

        if self._session:
            self._session.close()
            self._session = None

        self._background_thread = None

    def _run_background_loop(self) -> None:
        """Target function for the background thread. Runs the batching loop."""
        current_metrics: Optional[AggregatedMetrics] = None
        last_send_time = time.monotonic()

        while not self._stop_event.is_set():
            time_since_last_send = time.monotonic() - last_send_time
            remaining_time_in_interval = max(
                0, self.batch_interval_seconds - time_since_last_send
            )
            get_timeout = remaining_time_in_interval if not current_metrics else 0.01

            try:
                item = self._thread_safe_queue.get(block=True, timeout=get_timeout)

                if item is None:
                    break

                current_metrics = item
                self._thread_safe_queue.task_done()
                last_send_time = time.monotonic()

            except queue.Empty:
                if current_metrics and (
                    time.monotonic() - last_send_time >= self.batch_interval_seconds
                ):
                    self._flush_metrics(current_metrics)
                    current_metrics = None
                    last_send_time = time.monotonic()
            except Exception:
                pass
                time.sleep(1)

        while True:
            try:
                item = self._thread_safe_queue.get_nowait()
                if item is None:
                    self._thread_safe_queue.task_done()
                    continue
                current_metrics = item
                self._thread_safe_queue.task_done()
                self._flush_metrics(current_metrics)
                current_metrics = None
            except queue.Empty:
                break

        if current_metrics:
            self._flush_metrics(current_metrics)

    def _flush_metrics(self, metrics: AggregatedMetrics) -> None:
        """Flushes the provided batch using the requests session."""
        if not self._session:
            return

        try:
            self._send_metrics(metrics, self._session)
        except VigilantError as e:
            raise e
        except Exception as e:
            raise BatcherInternalServerError(
                f"Unexpected error sending Vigilant batch: {e}"
            ) from e

    def _send_metrics(
        self, metrics: AggregatedMetrics, session: requests.Session
    ) -> None:
        """Sends a batch of messages using the provided requests session."""
        payload: Dict[str, Any] = {
            "token": self.token,
            "metrics_counters": [
                metric.to_json() for metric in metrics.counter_metrics
            ],
            "metrics_gauges": [metric.to_json() for metric in metrics.gauge_metrics],
            "metrics_histograms": [
                metric.to_json() for metric in metrics.histogram_metrics
            ],
        }

        try:
            response = session.post(self.endpoint, json=payload, timeout=10)
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            if e.response is not None:
                if e.response.status_code == 401:
                    raise BatcherInvalidTokenError(
                        "Invalid token (401 Unauthorized)"
                    ) from e
                else:
                    raise BatcherInternalServerError(
                        f"Server error ({e.response.status_code}): {e.response.text}"
                    ) from e
            else:
                raise BatcherInternalServerError(
                    f"HTTP error without response: {e}"
                ) from e
        except requests.exceptions.Timeout:
            raise BatcherInternalServerError(f"HTTP request timed out after 10 seconds")
        except requests.exceptions.ConnectionError as e:
            raise BatcherInternalServerError(f"HTTP connection failed: {e}") from e
        except requests.exceptions.RequestException as e:
            raise BatcherInternalServerError(f"HTTP request failed: {e}") from e
