import json
import time
import threading
import queue
import requests
from typing import Dict, Any, List, Optional

global_metrics_handler: Optional['MetricsHandler'] = None


def init_metrics_handler(
    name: str = "app-name",
    token: str = "tk_1234567890",
    endpoint: str = "ingress.vigilant.run",
    insecure: bool = False,
    noop: bool = False
):
    global global_metrics_handler
    global_metrics_handler = MetricsHandler(
        name=name,
        token=token,
        endpoint=endpoint,
        insecure=insecure,
        noop=noop
    )

    return global_metrics_handler


def shutdown_metrics_handler():
    global global_metrics_handler
    if global_metrics_handler is not None:
        global_metrics_handler.shutdown()
        global_metrics_handler = None


def emit_metric(name: str, value: float, attrs: Dict[str, str] = None):
    global global_metrics_handler
    if global_metrics_handler is not None:
        global_metrics_handler.emit_metric(name, value, attrs)


class MetricsHandler:
    def __init__(self,
                 name: str = "app-name",
                 endpoint: str = "ingress.vigilant.run",
                 token: str = "tk_1234567890",
                 insecure: bool = False,
                 noop: bool = False):
        self.name = name
        self.endpoint = endpoint
        self.token = token
        self.insecure = insecure
        self.noop = noop

        self.metrics_queue = queue.Queue(maxsize=1000)
        self.batch_stop = threading.Event()
        self.batch_thread = None
        self._start_batcher()

    def emit_metric(self, name: str, value: float, attrs: Dict[str, str] = None):
        self._emit_metric(name, value, attrs)

    def shutdown(self):
        self._stop_batcher()

    def _emit_metric(self, name: str, value: float, attrs: Dict[str, str] = None):
        if self.noop:
            return

        metric_record = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time())),
            "name": name,
            "value": value,
            "attributes": {
                **(attrs or {}),
                "service.name": self.name,
            },
        }

        try:
            self.metrics_queue.put_nowait(metric_record)
        except queue.Full:
            pass

    def _start_batcher(self):
        self.batch_thread = threading.Thread(
            target=self._run_batcher, daemon=True
        )
        self.batch_thread.start()

    def _stop_batcher(self):
        self.batch_stop.set()

        remaining_metrics = []
        while True:
            try:
                metric = self.metrics_queue.get_nowait()
                remaining_metrics.append(metric)
            except queue.Empty:
                break

        if remaining_metrics:
            self._send_batch(remaining_metrics)

        if self.batch_thread is not None:
            self.batch_thread.join()

    def _run_batcher(self):
        max_batch_size = 100
        batch_interval = 0.1
        buffer: List[Dict[str, Any]] = []

        while not self.batch_stop.is_set():
            try:
                metric = self.metrics_queue.get(timeout=batch_interval)
                if metric is not None:
                    buffer.append(metric)

                if len(buffer) >= max_batch_size:
                    self._send_batch(buffer)
                    buffer.clear()

            except queue.Empty:
                if buffer:
                    self._send_batch(buffer)
                    buffer.clear()

        if buffer:
            self._send_batch(buffer)

    def _send_batch(self, metrics: List[Dict[str, Any]]):
        if not metrics or self.noop:
            return

        payload = {
            "token": self.token,
            "type": "metrics",
            "metrics": metrics,
        }

        try:
            headers = {"Content-Type": "application/json"}
            resp = requests.post(
                f"{'http' if self.insecure else 'https'}://{self.endpoint}/api/message",
                data=json.dumps(payload),
                headers=headers,
            )
            resp.raise_for_status()
        except Exception:
            pass
