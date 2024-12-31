import threading
import queue
import time
import traceback
import requests
import sys
import platform
import json
from typing import Optional, Dict, Any, List
import inspect

EVENTS_PATH = "/api/events"


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
        metadata (Dict[str, str]): Metadata about the event context.
    """

    def __init__(
        self,
        timestamp: float,
        message: Optional[str],
        exceptions: List[Dict[str, Any]],
        metadata: Dict[str, str],
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
        event = self._parse_message(message)
        try:
            self.queue.put_nowait(event)
        except queue.Full:
            # If the queue is full, we drop the event or handle accordingly
            pass

    def capture_error(self, err: Exception) -> None:
        """
        Captures and enqueues an error event.
        """
        if self.options.noop:
            return
        event = self._parse_error(err)
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

            # If it's time to flush, or queue is empty but there's leftover in batch
            if now >= next_flush_time:
                self._flush_batch()
                next_flush_time = now + (flush_interval_ms / 1000.0)
            else:
                # Wait for the queue or for the next flush time
                sleep_time = min(next_flush_time - now, 0.1)
                try:
                    event = self.queue.get(timeout=sleep_time)
                    with self.lock:
                        self.batch.append(event)
                except queue.Empty:
                    pass

        # On shutdown, flush any remaining events
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
        """ Sends the current batch of events to the server, if any exist. """
        with self.lock:
            to_send = self.batch[:]
            self.batch = []

        if not to_send or self.options.noop:
            return

        data = []
        for event in to_send:
            data.append({
                "Timestamp": event.timestamp,
                "Message": event.message,
                "Exceptions": event.exceptions,
                "Metadata": event.metadata,
            })

        try:
            response = self._send_batch(data)
            if response.status_code < 200 or response.status_code >= 300:
                # If there's a server error, handle logging or retry as needed
                print(
                    f"Event server returned status code {response.status_code}",
                    file=sys.stderr
                )
        except Exception as send_err:
            # Handle exceptions from requests
            print(f"Failed to send events: {send_err}", file=sys.stderr)

    def _send_batch(self, data: List[Dict[str, Any]]) -> requests.Response:
        """ Actual network call to post batched events to the server. """
        headers = {
            "Content-Type": "application/json",
            "x-vigilant-token": self.options.token,
        }
        # If insecure is True, we skip TLS verification
        verify_tls = not self.options.insecure
        return requests.post(
            self.options.url,
            headers=headers,
            data=json.dumps(data),
            timeout=self.client_timeout,
            verify=verify_tls
        )

    def _parse_message(self, message: str) -> InternalEvent:
        """ Creates an InternalEvent object from a message. """
        return InternalEvent(
            timestamp=time.time(),
            message=message,
            exceptions=[],
            metadata=self._get_metadata(),
        )

    def _parse_error(self, err: Exception) -> InternalEvent:
        """ Creates an InternalEvent object from an error. """
        exc_type = type(err)
        exc_name = exc_type.__name__
        exc_msg = str(err)
        return InternalEvent(
            timestamp=time.time(),
            message=None,
            exceptions=[{
                "Type": exc_name,
                "Value": exc_msg,
                "Stack": self._get_stack_trace(err),
            }],
            metadata=self._get_metadata(),
        )

    def _get_metadata(self) -> Dict[str, str]:
        """
        Gather some metadata about the context of the error/message,
        including function name, file name, line number, OS, etc.
        """
        filename, line, function = self._caller_info(skip=3)
        md = {
            "service": self.options.name,
            "function": function,
            "filename": filename,
            "line": str(line),
            "os": sys.platform,
            "arch": platform.machine(),
            "python.version": platform.python_version(),
            "stack": "".join(traceback.format_stack(limit=20)),
        }
        return md

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

    def _get_stack_trace(self, err: Exception) -> str:
        """ Returns a formatted traceback for the given exception. """
        return "".join(traceback.format_exception(type(err), err, err.__traceback__))


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
