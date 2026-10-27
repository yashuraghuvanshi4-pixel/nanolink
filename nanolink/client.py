"""Zero-dependency Python SDK client for Nanolink API."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class NanolinkError(Exception):
    """Base exception for all client errors."""


class NanolinkAPIError(NanolinkError):
    """Exception raised when API server returns a 4xx or 5xx status."""

    def __init__(self, status_code: int, message: str, payload: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(f"API Error [{status_code}]: {message}")
        self.status_code = status_code
        self.message = message
        self.payload = payload or {}


class NanolinkClient:
    """Synchronous HTTP client for interacting with a Nanolink instance."""

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        timeout: float = 10.0,
        headers: Optional[Dict[str, str]] = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.default_headers = headers or {}

    def _request(
        self,
        method: str,
        path: str,
        body: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        if params:
            qs = urlencode({k: v for k, v in params.items() if v is not None})
            if qs:
                url = f"{url}?{qs}"

        data = json.dumps(body).encode("utf-8") if body is not None else None
        req = Request(url, data=data, method=method)
        req.add_header("User-Agent", "NanolinkClient/Python")
        req.add_header("Accept", "application/json")
        if data is not None:
            req.add_header("Content-Type", "application/json; charset=utf-8")

        for k, v in self.default_headers.items():
            req.add_header(k, v)

        try:
            with urlopen(req, timeout=self.timeout) as resp:
                resp_data = resp.read().decode("utf-8")
                return json.loads(resp_data) if resp_data else {}
        except HTTPError as e:
            raw_err = e.read().decode("utf-8")
            try:
                err_json = json.loads(raw_err)
                msg = err_json.get("error", raw_err)
            except Exception:
                err_json = {}
                msg = raw_err or str(e)
            raise NanolinkAPIError(status_code=e.code, message=msg, payload=err_json) from e
        except URLError as e:
            raise NanolinkError(f"Connection failed to {url}: {e.reason}") from e

    def health(self) -> Dict[str, Any]:
        """Check API service health."""
        return self._request("GET", "/health")

    def shorten(
        self,
        url: str,
        alias: Optional[str] = None,
        title: Optional[str] = None,
        ttl_seconds: Optional[int] = None,
        tags: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Shorten a target destination URL."""
        payload: Dict[str, Any] = {"url": url}
        if alias:
            payload["alias"] = alias
        if title:
            payload["title"] = title
        if ttl_seconds:
            payload["ttl_seconds"] = ttl_seconds
        if tags:
            payload["tags"] = tags
        return self._request("POST", "/api/shorten", body=payload)

    def bulk_shorten(self, items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Shorten multiple URLs in a single request."""
        return self._request("POST", "/api/bulk-shorten", body={"items": items})

    def get_stats(self, code: str) -> Dict[str, Any]:
        """Retrieve real-time telemetry and metrics for a short code."""
        return self._request("GET", f"/api/stats/{code}")

    def list_links(self, limit: int = 50, offset: int = 0) -> Dict[str, Any]:
        """List active short links."""
        return self._request("GET", "/api/links", params={"limit": limit, "offset": offset})

    def search(self, query: str, limit: int = 50) -> Dict[str, Any]:
        """Search links by query keyword."""
        return self._request("GET", "/api/search", params={"q": query, "limit": limit})
