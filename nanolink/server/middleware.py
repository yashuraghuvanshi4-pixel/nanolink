"""Middleware pipeline and interceptors for HTTP requests."""

from __future__ import annotations

import time
from typing import Callable, Dict, List, Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from http.server import BaseHTTPRequestHandler


class BaseMiddleware:
    """Base class for HTTP request and response middleware."""

    def process_request(self, handler: BaseHTTPRequestHandler) -> Optional[bool]:
        """Called before request dispatch. Return False to abort further processing."""
        return True

    def process_response(
        self,
        handler: BaseHTTPRequestHandler,
        status: int,
        headers: Dict[str, str],
    ) -> Tuple[int, Dict[str, str]]:
        """Called before headers are sent. Can modify status or headers."""
        return status, headers


class CORSMiddleware(BaseMiddleware):
    """Injects standard Cross-Origin Resource Sharing (CORS) headers."""

    def __init__(
        self,
        allow_origin: str = "*",
        allow_methods: str = "GET, POST, OPTIONS, DELETE",
        allow_headers: str = "Content-Type, Authorization, X-Requested-With",
    ) -> None:
        self.allow_origin = allow_origin
        self.allow_methods = allow_methods
        self.allow_headers = allow_headers

    def process_response(
        self,
        handler: BaseHTTPRequestHandler,
        status: int,
        headers: Dict[str, str],
    ) -> Tuple[int, Dict[str, str]]:
        headers["Access-Control-Allow-Origin"] = self.allow_origin
        headers["Access-Control-Allow-Methods"] = self.allow_methods
        headers["Access-Control-Allow-Headers"] = self.allow_headers
        return status, headers


class TimingMiddleware(BaseMiddleware):
    """Measures request duration and injects X-Response-Time header."""

    def process_request(self, handler: BaseHTTPRequestHandler) -> Optional[bool]:
        setattr(handler, "_request_start_time", time.perf_counter())
        return True

    def process_response(
        self,
        handler: BaseHTTPRequestHandler,
        status: int,
        headers: Dict[str, str],
    ) -> Tuple[int, Dict[str, str]]:
        start = getattr(handler, "_request_start_time", None)
        if start is not None:
            elapsed_ms = (time.perf_counter() - start) * 1000.0
            headers["X-Response-Time"] = f"{elapsed_ms:.2f}ms"
        return status, headers


class MiddlewarePipeline:
    """Manages and executes an ordered chain of middleware."""

    def __init__(self, middlewares: Optional[List[BaseMiddleware]] = None) -> None:
        self.middlewares: List[BaseMiddleware] = middlewares or []

    def add(self, middleware: BaseMiddleware) -> None:
        self.middlewares.append(middleware)

    def execute_pre(self, handler: BaseHTTPRequestHandler) -> bool:
        """Runs pre-request hooks. Returns False if any middleware halts."""
        for mw in self.middlewares:
            res = mw.process_request(handler)
            if res is False:
                return False
        return True

    def execute_post(
        self,
        handler: BaseHTTPRequestHandler,
        status: int,
        headers: Dict[str, str],
    ) -> Tuple[int, Dict[str, str]]:
        """Runs post-request hooks in reverse order."""
        for mw in reversed(self.middlewares):
            status, headers = mw.process_response(handler, status, headers)
        return status, headers
