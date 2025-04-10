import uuid
import time
import json
from typing import Optional, TypedDict
from vigilant_sdk.attributes import add_attributes_async
from vigilant_sdk.logs import log_info

try:
    import fastapi
    from fastapi import Request
    _FASTAPI_INSTALLED = True
except ImportError:
    _FASTAPI_INSTALLED = False

    class Request:
        pass


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
        f"Incoming request for {request.url}, method: {request.method}",
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
        f"Outgoing response for {request.url}, method: {request.method}",
        {
            "request.method": request.method,
            "request.url": str(request.url),
            "response.status": str(response.status_code),
            "response.duration": f"{(time.time() - start) * 1000:.2f}ms",
        },
    )
    return response


class MiddlewareConfig(TypedDict):
    """
    MiddlewareConfig is used to configure the Vigilant middleware for FastAPI.
    """
    # Should add tracing middleware (default: True)
    with_tracing: Optional[bool]

    # Should add logging middleware (default: True)
    with_logging: Optional[bool]


def add_middleware(app: fastapi.FastAPI, config: Optional[MiddlewareConfig] = None):
    """
    Sets up the Vigilant SDK integration for a FastAPI application.
    """
    if not _FASTAPI_INSTALLED:
        raise ImportError(
            "FastAPI integration requires the 'fastapi' extra."
            "Install with: pip install vigilant-sdk[fastapi]"
        )
    middleware_config = _merge_middleware_config(config)

    if middleware_config["with_tracing"]:
        app.middleware("http")(tracing_middleware)

    if middleware_config["with_logging"]:
        app.middleware("http")(logging_middleware)


def _format_request_body(request_body_str_raw: str) -> str:
    try:
        request_body_obj = json.loads(request_body_str_raw)
        return json.dumps(request_body_obj, indent=2)
    except json.JSONDecodeError:
        return request_body_str_raw


def _format_request_headers(request_headers: dict) -> str:
    headers_dict = {str(k): str(v) for k, v in request_headers.items()}
    return json.dumps(headers_dict, indent=2)


_default_middleware_config: MiddlewareConfig = {
    "with_tracing": True,
    "with_logging": True,
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
