import uuid
import time
import json
import functools
import traceback
from typing import Optional, TypedDict
from fastapi.websockets import WebSocketDisconnect
from vigilant_sdk.attributes import add_attributes_async
from vigilant_sdk.logs import log_info, log_error
from vigilant_sdk.alerts import create_alert

try:
    import fastapi
    from fastapi import Request, WebSocket
    from fastapi.responses import JSONResponse
    _FASTAPI_INSTALLED = True
except ImportError:
    _FASTAPI_INSTALLED = False

    class Request:
        pass


class MiddlewareConfig(TypedDict):
    """
    MiddlewareConfig is used to configure the Vigilant middleware for FastAPI.
    """
    # Should add tracing middleware (default: True)
    with_tracing: Optional[bool]

    # Should add logging middleware (default: True)
    with_logging: Optional[bool]

    # Should add alert middleware (default: True)
    with_alerting: Optional[bool]


_default_middleware_config: MiddlewareConfig = {
    "with_tracing": True,
    "with_logging": True,
    "with_alerting": True,
}


def _merge_middleware_config(
    user_config: Optional[MiddlewareConfig] = None,
    default_config: MiddlewareConfig = _default_middleware_config
) -> MiddlewareConfig:
    user_config_dict = user_config or {}
    merged_dict = {**default_config, **user_config_dict}
    final_config = {k: merged_dict[k]
                    for k in MiddlewareConfig.__annotations__ if k in merged_dict}
    return final_config


async def tracing_middleware(request: Request, call_next):
    """
    FastAPI middleware to add a trace id to the request.
    """
    trace_id = str(uuid.uuid4())
    attributes = {
        "trace.id": trace_id,
    }

    async def next_with_context():
        return await call_next(request)

    return await add_attributes_async(attributes, next_with_context)


async def logging_middleware(request: Request, call_next):
    """
    FastAPI middleware to log request/response metadata including the request body.
    """
    original_receive = request.receive
    body_bytes = await request.body()
    body_yielded = False

    async def new_receive():
        nonlocal body_yielded
        if not body_yielded:
            body_yielded = True
            return {"type": "http.request", "body": body_bytes, "more_body": False}
        else:
            return await original_receive()

    request._receive = new_receive
    request_body = body_bytes.decode('utf-8', errors='replace')
    request_body_str = _format_request_body(request_body)
    request_headers_str = _format_request_headers(request.headers)

    log_info(
        f"Request for url: {request.url}, method: {request.method}",
        {
            "request.method": request.method,
            "request.url": str(request.url),
            "request.body": request_body_str,
            "request.headers": request_headers_str,
        },
    )
    start = time.time()

    response = await call_next(request)

    log_info(
        f"Response for url: {request.url}, method: {request.method}, status: {response.status_code}, duration: {(time.time() - start) * 1000:.2f}ms",
        {
            "request.method": request.method,
            "request.url": str(request.url),
            "response.status": str(response.status_code),
            "response.duration": f"{(time.time() - start) * 1000:.2f}ms",
        },
    )
    return response


async def alerting_middleware(request: Request, call_next):
    """
    FastAPI middleware to alert on errors.
    """
    try:
        return await call_next(request)
    except Exception as e:
        create_alert(
            f"Unhandled exception for route {request.scope.get('route').path}",
            {
                "error.name": str(type(e).__name__),
                "error.message": str(e),
                "error.stack": str(traceback.format_exc()),
            },
        )
        return JSONResponse(
            status_code=500,
            content={"message": "An unexpected error occurred."},
        )


def add_http_middleware(app: fastapi.FastAPI, config: Optional[MiddlewareConfig] = None):
    """
    Sets up the Vigilant SDK integration for a FastAPI application.
    """
    if not _FASTAPI_INSTALLED:
        raise ImportError(
            "FastAPI integration requires the 'fastapi' extra."
            "Install with: pip install vigilant-sdk[fastapi]"
        )
    middleware_config = _merge_middleware_config(config)

    if middleware_config["with_alerting"]:
        app.middleware("http")(alerting_middleware)

    if middleware_config["with_logging"]:
        app.middleware("http")(logging_middleware)

    if middleware_config["with_tracing"]:
        app.middleware("http")(tracing_middleware)


def _format_request_body(request_body_str_raw: str) -> str:
    try:
        request_body_obj = json.loads(request_body_str_raw)
        return json.dumps(request_body_obj, indent=2)
    except json.JSONDecodeError:
        return request_body_str_raw


def _format_request_headers(request_headers: dict) -> str:
    headers_dict = {str(k): str(v) for k, v in request_headers.items()}
    return json.dumps(headers_dict, indent=2)


class WrappedWebSocket:
    """
    Wraps a WebSocket to add logging and tracing.
    """

    def __init__(self, websocket: WebSocket, config: MiddlewareConfig):
        self._websocket = websocket
        self._config = config

    async def accept(self, *args, **kwargs):
        if self._config["with_logging"]:
            log_info(
                f"WebSocket accepted")
        await self._websocket.accept(*args, **kwargs)

    async def receive_text(self):
        try:
            data = await self._websocket.receive_text()
            if self._config["with_logging"]:
                log_info(f"WebSocket received text: {data}")
            return data
        except WebSocketDisconnect as e:
            log_info(f"WebSocket client disconnect: {e}")
            raise e

    async def receive_bytes(self):
        try:
            data = await self._websocket.receive_bytes()
            if self._config["with_logging"]:
                log_info(f"WebSocket received bytes: {len(data)} bytes")
            return data
        except WebSocketDisconnect as e:
            log_info(f"WebSocket client disconnect: {e}")
            raise e

    async def receive_json(self):
        try:
            data = await self._websocket.receive_json()
            if self._config["with_logging"]:
                log_info(f"WebSocket received JSON: {data}")
            return data
        except WebSocketDisconnect as e:
            log_info(f"WebSocket client disconnect: {e}")
            raise e

    async def send_text(self, data: str):
        if self._config["with_logging"]:
            log_info(f"WebSocket sending text: {data}")
        await self._websocket.send_text(data)

    async def send_bytes(self, data: bytes):
        if self._config["with_logging"]:
            log_info(f"WebSocket sending bytes: {len(data)} bytes")
        await self._websocket.send_bytes(data)

    async def send_json(self, data: dict):
        if self._config["with_logging"]:
            log_info(f"WebSocket sending JSON: {data}")
        await self._websocket.send_json(data)

    async def close(self, code: int = 1000, reason: Optional[str] = None):
        if self._config["with_logging"]:
            log_info(
                f"WebSocket server close with code: {code}, reason: {reason}")
        await self._websocket.close(code=code, reason=reason)

    def __getattr__(self, item):
        return getattr(self._websocket, item)


def add_websocket_middleware(func=None, config: Optional[MiddlewareConfig] = None):
    """
    Adds middleware to a WebSocket endpoint. Used as a decorator.
    """
    if func is None:
        return lambda f: add_websocket_middleware(f, config=config)

    _middleware_config = _merge_middleware_config(config)

    @functools.wraps(func)
    async def wrapper(websocket: WebSocket, *args, **kwargs):
        _connection_id = str(uuid.uuid4())
        wrapped_ws = WrappedWebSocket(websocket, _middleware_config)
        try:
            async def func_with_context():
                return await func(wrapped_ws, *args, **kwargs)

            if _middleware_config["with_tracing"]:
                attributes = {"connection.id": _connection_id}
                await add_attributes_async(attributes, func_with_context)
            else:
                await func_with_context()
        except Exception as e:
            log_error(f"WebSocket error: {e}")
            raise e

    return wrapper
