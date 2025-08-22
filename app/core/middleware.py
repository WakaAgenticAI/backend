from __future__ import annotations
import time
import uuid
from typing import Callable

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response


class RequestIDMiddleware(BaseHTTPMiddleware):
    header_name = "X-Request-ID"

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        req_id = request.headers.get(self.header_name) or str(uuid.uuid4())
        request.state.request_id = req_id
        response: Response = await call_next(request)
        response.headers[self.header_name] = req_id
        return response


class SimpleRateLimitMiddleware(BaseHTTPMiddleware):
    """Very simple in-memory rate limiter per client IP.
    Not production grade. For multi-process deployments, use Redis/ginger or Starlette-limiter.
    """

    buckets: dict[str, list[float]] = {}

    def __init__(self, app, max_requests: int = 100, window_seconds: int = 60):
        super().__init__(app)
        self.max_requests = max_requests
        self.window = window_seconds

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        client_ip = request.client.host if request.client else "unknown"
        now = time.time()
        window_start = now - self.window

        bucket = self.buckets.setdefault(client_ip, [])
        # prune old
        while bucket and bucket[0] < window_start:
            bucket.pop(0)
        bucket.append(now)

        if len(bucket) > self.max_requests:
            # 429 Too Many Requests
            return Response("Too Many Requests", status_code=429)

        return await call_next(request)
