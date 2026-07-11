import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from src.logging_config import request_id_ctx

logger = logging.getLogger("app")


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Give every request an id, time it, and echo both back on the response.

    - `X-Request-ID`: reused from the incoming header if a client/proxy set one,
      otherwise generated. Stashed on `request.state` so error responses and logs
      can reference the same id.
    - `X-Process-Time-ms`: how long the handler took — a cheap, always-on timing signal.
    """

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id
        request_id_ctx.set(request_id)          # so every log line in this request carries it

        start = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - start) * 1000

        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time-ms"] = f"{elapsed_ms:.2f}"
        logger.info("%s %s -> %s (%.2f ms) [%s]",
                    request.method, request.url.path, response.status_code, elapsed_ms, request_id)
        return response
