from __future__ import annotations
import html
import re
import time
import uuid
from typing import Callable

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response


class RequestIDMiddleware(BaseHTTPMiddleware):
    header_name = "X-Request-ID"

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        req_id = request.headers.get(self.header_name) or str(uuid.uuid4())
        request.state.request_id = req_id
        response: Response = await call_next(request)
        response.headers[self.header_name] = req_id
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to every response to prevent XSS, clickjacking, MIME sniffing."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response: Response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(self), geolocation=()"
        # Strict CSP for API responses
        response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response


class InputSanitizationMiddleware(BaseHTTPMiddleware):
    """Reject oversized requests and log suspicious patterns (SQL injection, XSS)."""

    # Patterns that indicate potential injection attacks
    SUSPICIOUS_PATTERNS = [
        re.compile(r"(<script[^>]*>)", re.IGNORECASE),
        re.compile(r"(javascript\s*:)", re.IGNORECASE),
        re.compile(r"(on\w+\s*=\s*[\"'])", re.IGNORECASE),  # onclick=, onerror=, etc.
    ]

    def __init__(self, app, max_body_mb: int = 10):
        super().__init__(app)
        self.max_body_bytes = max_body_mb * 1024 * 1024

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Check Content-Length header for oversized requests
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.max_body_bytes:
            return JSONResponse(
                {"detail": "Request body too large"},
                status_code=413,
            )

        # For POST/PUT/PATCH, read body and check for suspicious patterns
        if request.method in ("POST", "PUT", "PATCH"):
            body = await request.body()
            if len(body) > self.max_body_bytes:
                return JSONResponse(
                    {"detail": "Request body too large"},
                    status_code=413,
                )
            body_str = body.decode("utf-8", errors="ignore")
            for pattern in self.SUSPICIOUS_PATTERNS:
                if pattern.search(body_str):
                    import logging
                    logger = logging.getLogger("security")
                    client_ip = request.client.host if request.client else "unknown"
                    logger.warning(
                        "suspicious_input_blocked",
                        extra={"ip": client_ip, "path": str(request.url.path), "pattern": pattern.pattern},
                    )
                    return JSONResponse(
                        {"detail": "Request contains potentially unsafe content"},
                        status_code=400,
                    )

        return await call_next(request)


class LoginRateLimitMiddleware(BaseHTTPMiddleware):
    """Brute-force protection: limit login attempts per IP."""

    _attempts: dict[str, list[float]] = {}

    def __init__(self, app, max_attempts: int = 5, window_seconds: int = 900):
        super().__init__(app)
        self.max_attempts = max_attempts
        self.window = window_seconds

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Only apply to login endpoint
        if request.url.path.endswith("/auth/login") and request.method == "POST":
            client_ip = request.client.host if request.client else "unknown"
            now = time.time()
            window_start = now - self.window

            bucket = self._attempts.setdefault(client_ip, [])
            # Prune old attempts
            while bucket and bucket[0] < window_start:
                bucket.pop(0)

            if len(bucket) >= self.max_attempts:
                retry_after = int(bucket[0] + self.window - now)
                return JSONResponse(
                    {"detail": f"Too many login attempts. Try again in {retry_after} seconds."},
                    status_code=429,
                    headers={"Retry-After": str(retry_after)},
                )

            bucket.append(now)

        return await call_next(request)


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
