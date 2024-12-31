import threading
import queue
import time
import traceback
import requests
import sys
import platform
import json
from typing import Optional, Dict, Any, List, Tuple
import inspect
from datetime import datetime

EVENTS_PATH = "/api/events"
PROHIBITED_MODULES = [
    "site-packages",
    "dist-packages",
    "python3",
    "lib/python",
    "tests/",
    "testing/",
    "vendor/",
    "third_party/",
    "vigilant",
]


class EventHandlerOptions:
    """
    Configuration options for the EventHandler.

    Attributes:
        url (str): The URL of the event handler (e.g. 'https://errors.vigilant.run/api/events')
        token (str): Authentication token for the event handler
        name (str): Name of the service sending events
        insecure (bool): Whether to ignore TLS verification
        noop (bool): If True, events are not actually sent
    """

    def __init__(self):
        self.url: str = "https://errors.vigilant.run"
        self.token: str = "tk_1234567890"
        self.name: str = "python-service"
        self.insecure: bool = False
        self.noop: bool = False


class InternalEvent:
    """
    Internal representation of an event.

    Attributes:
        timestamp (float): The UNIX timestamp of when the event occurred.
        message (Optional[str]): The event message (if any).
        exceptions (List[Dict[str, Any]]): A list of exception information.
        metadata (Dict[str, Any]): Metadata about the event context.
    """

    def __init__(
        self,
        timestamp: float,
        message: Optional[str],
        exceptions: List[Dict[str, Any]],
        metadata: Dict[str, Any],
    ):
        self.timestamp = timestamp
        self.message = message
        self.exceptions = exceptions
        self.metadata = metadata


class EventHandler:
    """
    The EventHandler consumes messages and errors, batches them,
    and periodically sends them to the specified event server.
    """

    def __init__(self, options: EventHandlerOptions):
        self.options = options
        self.queue = queue.Queue(maxsize=1000)
        self.batch: List[InternalEvent] = []
        self.lock = threading.Lock()
        self.stop_event = threading.Event()
        self.worker_thread = threading.Thread(
            target=self._worker_loop, daemon=True
        )
        self.client_timeout = 5
        self.worker_thread.start()

    def capture_message(self, message: str) -> None:
        """
        Captures and enqueues a message event.
        """
        if self.options.noop:
            return
        event = InternalEvent(
            timestamp=time.time(),
            message=message,
            exceptions=[],
            metadata=self._get_metadata()
        )
        try:
            self.queue.put_nowait(event)
        except queue.Full:
            pass

    def capture_error(self, err: Exception) -> None:
        """
        Captures and enqueues an error event.
        """
        if self.options.noop:
            return
        exc_name = type(err).__name__
        exc_msg = str(err)
        frames = self._get_stack_frames(skip=2)

        event = InternalEvent(
            timestamp=time.time(),
            message=None,
            exceptions=[{
                "type": exc_name,
                "value": exc_msg,
                "stack": frames
            }],
            metadata=self._get_metadata()
        )
        try:
            self.queue.put_nowait(event)
        except queue.Full:
            pass

    def shutdown(self):
        """
        Signals the worker to stop and waits for it to finish sending any remaining events.
        """
        self.stop_event.set()
        self.worker_thread.join()

    def _worker_loop(self):
        """
        Background thread that pulls events off the queue, batches them,
        and flushes them to the server periodically.
        """
        flush_interval_ms = 100
        next_flush_time = time.time() + (flush_interval_ms / 1000.0)

        while not self.stop_event.is_set():
            now = time.time()

            if now >= next_flush_time:
                self._flush_batch()
                next_flush_time = now + (flush_interval_ms / 1000.0)
            else:
                sleep_time = min(next_flush_time - now, 0.1)
                try:
                    event = self.queue.get(timeout=sleep_time)
                    with self.lock:
                        self.batch.append(event)
                except queue.Empty:
                    pass

        self._drain_queue()
        self._flush_batch()

    def _drain_queue(self):
        """ Pull remaining events out of the queue after stop is signaled. """
        while not self.queue.empty():
            try:
                event = self.queue.get_nowait()
                with self.lock:
                    self.batch.append(event)
            except queue.Empty:
                break

    def _flush_batch(self):
        """
        Sends the current batch of events to the server, if any exist,
        converting the data to match the Go struct definitions.
        """
        with self.lock:
            to_send = self.batch[:]
            self.batch = []

        if not to_send or self.options.noop:
            return

        data = []
        for event in to_send:
            iso_ts = datetime.utcfromtimestamp(
                event.timestamp).isoformat() + "Z"
            msg = event.message if event.message else None
            data.append({
                "timestamp": iso_ts,
                "message": msg,
                "exceptions": event.exceptions,
                "metadata": event.metadata
            })

        try:
            response = self._send_batch(data)
            if response.status_code < 200 or response.status_code >= 300:
                print(
                    f"Event server returned status code {response.status_code}",
                    file=sys.stderr
                )
        except Exception as send_err:
            print(f"Failed to send events: {send_err}", file=sys.stderr)

    def _send_batch(self, data: List[Dict[str, Any]]) -> requests.Response:
        """ Actual network call to post batched events to the server. """
        headers = {
            "Content-Type": "application/json",
            "x-vigilant-token": self.options.token,
        }
        verify_tls = not self.options.insecure
        return requests.post(
            self.options.url + EVENTS_PATH,
            headers=headers,
            data=json.dumps(data),
            timeout=self.client_timeout,
            verify=verify_tls
        )

    def _get_metadata(self) -> Dict[str, Any]:
        """
        Gathers metadata for an event, including a raw stack (similar to debug.Stack())
        and basic system info. This is somewhat analogous to the Go getMetadata().
        """
        filename, line, function = self._caller_info(skip=3)

        return {
            "service": self.options.name,
            "function": function,
            "filename": filename,
            "line": str(line),
            "os": sys.platform,
            "arch": platform.machine(),
            "python.version": platform.python_version(),
            "stack": "".join(traceback.format_stack(limit=25)),
        }

    def _caller_info(self, skip: int = 2):
        """
        Returns the caller's filename, line number, and function name.
        skip indicates how many frames to skip from the call site.
        """
        stack = inspect.stack()
        if len(stack) < skip + 1:
            return ("", 0, "")
        frame = stack[skip]
        return (frame.filename, frame.lineno, frame.function)

    def _get_stack_frames(self, skip: int = 0) -> List[Dict[str, Any]]:
        """
        Parse the Python call stack:
        - Reverse the frame list
        - Identify a 'module' and 'function'
        - Mark frames as internal vs external if they match PROHIBITED_MODULES
        """
        raw_stack = traceback.extract_stack(limit=50)
        stack_frames = raw_stack[:-skip] if skip > 0 else raw_stack

        frames = []
        for sf in stack_frames:
            function_full = sf.name
            filename = sf.filename
            lineno = sf.lineno

            module, function = self._split_function_name(function_full)

            is_internal = True
            for pmod in PROHIBITED_MODULES:
                if pmod in module or pmod in filename:
                    is_internal = False
                    break

            frames.append({
                "function": function,
                "module": module,
                "file": filename,
                "line": lineno,
                "internal": is_internal
            })

        frames.reverse()
        return frames

    def _split_function_name(self, name: str) -> Tuple[str, str]:
        """
        Splits a path-qualified function name into module + function.
        """
        if "." not in name:
            return ("", name)
        idx = name.rfind(".")
        return (name[:idx], name[idx+1:])


def create_event_handler(
    *,
    url: str,
    token: str,
    name: str,
    insecure: bool = False,
    noop: bool = False
) -> EventHandler:
    """
    Create a new EventHandler for sending events to Vigilant.

    Args:
        url (str): The base URL of the event handler (e.g., 'https://errors.vigilant.run')
        token (str): The authentication token for the event handler
        name (str): The name of the service sending events
        insecure (bool, optional): Whether to ignore TLS verification. Defaults to False.
        noop (bool, optional): If True, events are not actually sent. Defaults to False.

    Returns:
        EventHandler: A configured event handler instance ready to send events.

    Example:
        >>> handler = create_event_handler(
        ...     url="https://errors.vigilant.run",
        ...     token="tk_ABC123XYZ",
        ...     name="python-server",
        ...     insecure=True,
        ...     noop=False
        ... )
        >>> handler.capture_message("Hello from Python!")
    """
    options = EventHandlerOptions()
    options.url = url
    options.token = token
    options.name = name
    options.insecure = insecure
    options.noop = noop

    if not options.url:
        raise ValueError("Event handler URL is empty")
    if not options.token:
        raise ValueError("Event handler token is empty")

    return EventHandler(options)
