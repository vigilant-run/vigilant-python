import asyncio
import httpx
from typing import Generic, List, Optional, Dict, Any, TypeVar
from vigilant_sdk.message import (
    VigilantError,
    BatcherInvalidTokenError,
    BatcherInternalServerError,
)

T = TypeVar('T')


class Batcher(Generic[T]):
    """
    A class used to batch and send event batches asynchronously.
    """

    def __init__(
        self,
        endpoint: str,
        token: str,
        type_name: str,
        key: str,
        batch_interval_seconds: float,
        max_batch_size: int,
    ):
        self.endpoint: str = endpoint
        self.token: str = token
        self.type_name: str = type_name
        self.key: str = key
        self.batch_interval_seconds: float = batch_interval_seconds
        self.max_batch_size: int = max_batch_size

        self._queue: List[T] = []
        self._batcher_task: Optional[asyncio.Task] = None
        self._stop_event: asyncio.Event = asyncio.Event()
        self._flush_event: asyncio.Event = asyncio.Event()
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Initializes or returns the httpx client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient()
        return self._client

    def add(self, item: T) -> None:
        """Adds an item to the queue."""
        self._queue.append(item)
        if len(self._queue) >= self.max_batch_size:
            self._flush_event.set()

    async def start(self) -> None:
        """Starts the batcher background task."""
        if self._batcher_task is not None:
            return

        self._stop_event.clear()
        self._batcher_task = asyncio.create_task(self._run_batcher())

    async def shutdown(self) -> None:
        """Shuts down the batcher gracefully."""
        if self._batcher_task is None:
            return

        self._stop_event.set()
        self._flush_event.set()
        try:
            await asyncio.wait_for(self._batcher_task, timeout=None)
        except asyncio.CancelledError:
            pass
        finally:
            self._batcher_task = None
            await self._flush_batch(force=True)
            if self._client:
                await self._client.aclose()
                self._client = None

    async def _run_batcher(self) -> None:
        """The main loop for the batcher task."""
        while not self._stop_event.is_set():
            try:
                await asyncio.wait_for(
                    asyncio.shield(
                        asyncio.wait(
                            [
                                self._stop_event.wait(),
                                self._flush_event.wait(),
                                asyncio.sleep(self.batch_interval_seconds),
                            ],
                            return_when=asyncio.FIRST_COMPLETED,
                        )
                    ),
                    timeout=self.batch_interval_seconds + 1
                )
            except asyncio.TimeoutError:
                pass

            self._flush_event.clear()

            if self._queue:
                await self._flush_batch()

            if len(self._queue) >= self.max_batch_size:
                continue

        await self._flush_batch(force=True)

    async def _flush_batch(self, force: bool = False) -> None:
        """Flushes the queue by sending batches."""
        if not self._queue:
            return

        while self._queue:
            batch = self._queue[:self.max_batch_size]
            try:
                await self._send_batch(batch)
                self._queue = self._queue[self.max_batch_size:]
            except VigilantError as e:
                print(e)
                break
            except Exception as e:
                print(e)
                break

            if not force or not self._queue:
                break

    async def _send_batch(self, messages: List[T]) -> None:
        """Sends a batch of messages to the configured endpoint."""
        payload: Dict[str, Any] = {
            "token": self.token,
            "type": self.type_name,
            self.key: messages,
        }
        headers = {"Content-Type": "application/json"}
        client = await self._get_client()

        try:
            response = await client.post(self.endpoint, json=payload, headers=headers)
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise BatcherInvalidTokenError(
                    "Invalid token (401 Unauthorized)") from e
            else:
                raise BatcherInternalServerError(
                    f"Server error ({e.response.status_code}): {e.response.text}") from e
        except httpx.RequestError as e:
            raise BatcherInternalServerError(
                f"HTTP request failed: {e}") from e
