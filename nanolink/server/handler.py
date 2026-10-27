"""HTTP request handler for URL redirection, REST API, and analytics."""

from __future__ import annotations

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, Optional
from urllib.parse import parse_qs, urlparse

from nanolink import __version__
from nanolink.core.analytics import AnalyticsEngine
from nanolink.core.qr import QRCode
from nanolink.core.service import (
    LinkService,
    InvalidURLError,
    InvalidAliasError,
    AliasAlreadyExistsError,
    LinkNotFoundError,
    LinkExpiredError,
)
from nanolink.storage.db import Database


class NanolinkRequestHandler(BaseHTTPRequestHandler):
    """Handles HTTP redirection, analytics collection, and REST API endpoints."""

    server_version = f"nanolink/{__version__}"

    def __init__(self, *args, db: Optional[Database] = None, **kwargs) -> None:
        self.db = db or getattr(self, "default_db", Database())
        self.service = LinkService(self.db)
        self.analytics = AnalyticsEngine(self.db)
        super().__init__(*args, **kwargs)

    def log_message(self, format: str, *args: Any) -> None:
        """Suppress standard logging if quiet, or format nicely."""
        sys_stderr = getattr(self, "enable_logging", True)
        if sys_stderr:
            super().log_message(format, *args)

    def _send_json(self, status: int, payload: Dict[str, Any]) -> None:
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(data)

    def do_OPTIONS(self) -> None:
        """Handle CORS pre-flight requests."""
        self.send_response(HTTPStatus.NO_CONTENT)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS, DELETE")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        query = parse_qs(parsed.query)

        # Health check
        if path == "/health":
            self._send_json(HTTPStatus.OK, {"status": "ok", "version": __version__})
            return

        # API: Get link stats
        if path.startswith("/api/stats/"):
            code = path.split("/api/stats/", 1)[1]
            stats = self.analytics.get_link_stats(code)
            if stats is None:
                self._send_json(HTTPStatus.NOT_FOUND, {"error": f"Code '{code}' not found."})
            else:
                self._send_json(HTTPStatus.OK, stats.to_dict())
            return

        # API: Get QR code SVG
        if path.startswith("/api/qr/"):
            code = path.split("/api/qr/", 1)[1]
            try:
                link = self.service.resolve(code)
                host = self.headers.get("Host", "localhost:8000")
                qr = QRCode(f"http://{host}/{link.code}")
                svg_data = qr.to_svg().encode("utf-8")
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "image/svg+xml")
                self.send_header("Content-Length", str(len(svg_data)))
                self.end_headers()
                self.wfile.write(svg_data)
            except (LinkNotFoundError, LinkExpiredError) as err:
                self._send_json(HTTPStatus.NOT_FOUND, {"error": str(err)})
            return

        # API: List links
        if path == "/api/links":
            limit = int(query.get("limit", ["20"])[0])
            offset = int(query.get("offset", ["0"])[0])
            links = self.service.list_links(limit=limit, offset=offset)
            self._send_json(HTTPStatus.OK, {"links": [l.to_dict() for l in links]})
            return

        # Dashboard web UI
        if path in ("", "/", "/dashboard"):
            self._handle_root_ui()
            return

        # Code redirect: GET /{code}
        code = path.lstrip("/")
        self._handle_redirect(code)

    def _handle_redirect(self, code: str) -> None:
        client_ip = self.headers.get("X-Forwarded-For", self.client_address[0])
        user_agent = self.headers.get("User-Agent")
        referer = self.headers.get("Referer")

        try:
            link = self.service.resolve(code)
        except LinkNotFoundError:
            self._send_json(
                HTTPStatus.NOT_FOUND,
                {"error": f"Short link '{code}' does not exist."},
            )
            return
        except LinkExpiredError:
            self._send_json(
                HTTPStatus.GONE,
                {"error": f"Short link '{code}' has expired."},
            )
            return

        # Record analytics
        try:
            self.analytics.record_click(
                link_code=code,
                ip=client_ip,
                user_agent=user_agent,
                referer=referer,
            )
        except Exception:
            # Analytics recording failure should not block user redirection
            pass

        # 307 Temporary Redirect: preserves request method and guarantees client
        # doesn't cache permanently, allowing accurate real-time click counting!
        self.send_response(HTTPStatus.TEMPORARY_REDIRECT)
        self.send_header("Location", link.target_url)
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        self.end_headers()

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")

        if path == "/api/shorten":
            content_length = int(self.headers.get("Content-Length", 0))
            if content_length == 0:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": "Missing JSON request body."})
                return

            try:
                body = json.loads(self.rfile.read(content_length).decode("utf-8"))
            except Exception:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": "Malformed JSON payload."})
                return

            target_url = body.get("url")
            if not target_url:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": "Field 'url' is required."})
                return

            custom_alias = body.get("alias")
            title = body.get("title")
            ttl_seconds = body.get("ttl_seconds")
            max_clicks = body.get("max_clicks")

            try:
                link = self.service.shorten(
                    url=target_url,
                    custom_alias=custom_alias,
                    title=title,
                    ttl_seconds=ttl_seconds,
                    max_clicks=max_clicks,
                )
            except (InvalidURLError, InvalidAliasError) as err:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(err)})
                return
            except AliasAlreadyExistsError as err:
                self._send_json(HTTPStatus.CONFLICT, {"error": str(err)})
                return

            host = self.headers.get("Host", "localhost:8000")
            response_data = link.to_dict()
            response_data["short_url"] = f"http://{host}/{link.code}"

            self._send_json(HTTPStatus.CREATED, response_data)
            return

        self._send_json(HTTPStatus.NOT_FOUND, {"error": "Endpoint not found."})

    def _handle_root_ui(self) -> None:
        """Render embedded single-page web dashboard."""
        from nanolink.server.dashboard import DASHBOARD_HTML
        data = DASHBOARD_HTML.encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def create_handler_factory(db: Database):
    """Factory creating Handler with pre-configured Database."""
    class ConfiguredHandler(NanolinkRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, db=db, **kwargs)
    return ConfiguredHandler


def run_server(host: str = "127.0.0.1", port: int = 8000, db: Optional[Database] = None) -> int:
    """Launch multi-threaded HTTP server."""
    database = db or Database()
    handler_cls = create_handler_factory(database)
    server = ThreadingHTTPServer((host, port), handler_cls)
    print(f"⚡ nanolink server listening on http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down nanolink server...")
        server.server_close()
    return 0
