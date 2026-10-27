"""Data export utilities for analytics events (CSV and JSON)."""

from __future__ import annotations

import csv
import io
import json
from typing import Any, Dict, List
from nanolink.models import ClickEvent, LinkStats


def export_clicks_to_csv(clicks: List[ClickEvent]) -> str:
    """Export click telemetry records to an RFC 4180 CSV string."""
    output = io.StringIO()
    fieldnames = [
        "id",
        "link_code",
        "timestamp",
        "browser",
        "os",
        "device_type",
        "referer_domain",
        "country",
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()

    for click in clicks:
        writer.writerow({
            "id": click.id or "",
            "link_code": click.link_code,
            "timestamp": click.timestamp,
            "browser": click.browser,
            "os": click.os,
            "device_type": click.device_type,
            "referer_domain": click.referer_domain or "",
            "country": click.country or "Unknown",
        })

    return output.getvalue()


def export_stats_to_json(stats: LinkStats, indent: int = 2) -> str:
    """Export structured link statistics as JSON string."""
    return json.dumps(stats.to_dict(), indent=indent)
