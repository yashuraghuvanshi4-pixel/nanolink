"""Prometheus-compatible metrics collector and text exposition generator."""

from __future__ import annotations

import time
from collections import defaultdict
from typing import Dict, Tuple
from nanolink.storage.db import Database


class MetricsCollector:
    """Thread-safe Prometheus metrics collector."""

    def __init__(self) -> None:
        self.start_time = time.time()
        self.requests_total: Dict[Tuple[str, int], int] = defaultdict(int)
        self.redirects_total = 0

    def record_request(self, method: str, status_code: int) -> None:
        """Increment HTTP request counter."""
        self.requests_total[(method.upper(), status_code)] += 1

    def record_redirect(self) -> None:
        """Increment redirect counter."""
        self.redirects_total += 1

    def generate_prometheus_text(self, db: Database) -> str:
        """Generate Prometheus exposition format metrics string."""
        uptime = time.time() - self.start_time
        metrics = db.get_global_metrics()
        total_links = metrics.get("total_links", 0)
        total_clicks = metrics.get("total_clicks", 0)

        lines = [
            "# HELP nanolink_uptime_seconds Total runtime of nanolink server in seconds.",
            "# TYPE nanolink_uptime_seconds gauge",
            f"nanolink_uptime_seconds {uptime:.2f}",
            "",
            "# HELP nanolink_total_links Total registered short links.",
            "# TYPE nanolink_total_links gauge",
            f"nanolink_total_links {total_links}",
            "",
            "# HELP nanolink_total_clicks Total recorded redirects/clicks across all links.",
            "# TYPE nanolink_total_clicks counter",
            f"nanolink_total_clicks {total_clicks}",
            "",
            "# HELP nanolink_redirects_total Redirects served since server startup.",
            "# TYPE nanolink_redirects_total counter",
            f"nanolink_redirects_total {self.redirects_total}",
            "",
            "# HELP nanolink_http_requests_total Total HTTP requests handled by method and status.",
            "# TYPE nanolink_http_requests_total counter",
        ]

        if not self.requests_total:
            lines.append('nanolink_http_requests_total{method="GET",status="200"} 0')
        else:
            for (method, status), count in sorted(self.requests_total.items()):
                lines.append(f'nanolink_http_requests_total{{method="{method}",status="{status}"}} {count}')

        lines.append("")
        return "\n".join(lines)
