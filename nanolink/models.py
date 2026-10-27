"""Data models for short links, click telemetry, and aggregated analytics."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
import re

URL_REGEX = re.compile(
    r"^(https?://)"  # scheme
    r"(([a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}|localhost|(\d{1,3}\.){3}\d{1,3})"  # domain / host
    r"(:\d+)?"  # port
    r"(/[-a-zA-Z0-9%_.~+]*)*"  # path
    r"(\?[;&a-zA-Z0-9%_.~+=-]*)?"  # query string
    r"(#[-a-zA-Z0-9_]*)?$",  # fragment
    re.IGNORECASE,
)

ALIAS_REGEX = re.compile(r"^[a-zA-Z0-9_-]{3,64}$")


def validate_url(url: str) -> bool:
    """Validate that a URL starts with http(s) and matches RFC standards."""
    if not url or len(url) > 2048:
        return False
    return bool(URL_REGEX.match(url))


def validate_alias(alias: str) -> bool:
    """Validate custom alias syntax (alphanumeric, dashes, underscores, 3-64 chars)."""
    return bool(ALIAS_REGEX.match(alias))


def utc_now_iso() -> str:
    """Get current UTC timestamp in ISO 8601 format."""
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Link:
    """Represents a shortened link record."""

    code: str
    target_url: str
    title: Optional[str] = None
    created_at: str = field(default_factory=utc_now_iso)
    expires_at: Optional[str] = None
    max_clicks: Optional[int] = None
    click_count: int = 0
    is_active: bool = True
    id: Optional[int] = None

    def is_expired(self, current_time: Optional[datetime] = None) -> bool:
        """Check whether the link has expired due to time or click limit."""
        if not self.is_active:
            return True

        if self.max_clicks is not None and self.click_count >= self.max_clicks:
            return True

        if self.expires_at:
            now = current_time or datetime.now(timezone.utc)
            try:
                # Handle ISO timestamps with or without timezone
                exp = datetime.fromisoformat(self.expires_at)
                if exp.tzinfo is None:
                    exp = exp.replace(tzinfo=timezone.utc)
                if now >= exp:
                    return True
            except ValueError:
                pass

        return False

    def to_dict(self) -> Dict[str, Any]:
        """Convert link dataclass to dictionary."""
        data = asdict(self)
        data["is_expired"] = self.is_expired()
        return data

    @classmethod
    def from_row(cls, row: Any) -> "Link":
        """Instantiate Link from a sqlite3.Row or dict-like object."""
        return cls(
            id=row["id"],
            code=row["code"],
            target_url=row["target_url"],
            title=row["title"] if "title" in row.keys() else None,
            created_at=row["created_at"],
            expires_at=row["expires_at"] if "expires_at" in row.keys() else None,
            max_clicks=row["max_clicks"] if "max_clicks" in row.keys() else None,
            click_count=row["click_count"] if "click_count" in row.keys() else 0,
            is_active=bool(row["is_active"]) if "is_active" in row.keys() else True,
        )


@dataclass
class ClickEvent:
    """Telemetry recorded for each redirect event."""

    link_code: str
    timestamp: str = field(default_factory=utc_now_iso)
    ip_hash: str = ""
    user_agent: Optional[str] = None
    browser: str = "Unknown"
    os: str = "Unknown"
    device_type: str = "unknown"
    referer: Optional[str] = None
    referer_domain: Optional[str] = None
    country: Optional[str] = "Unknown"
    id: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_row(cls, row: Any) -> "ClickEvent":
        return cls(
            id=row["id"],
            link_code=row["link_code"],
            timestamp=row["timestamp"],
            ip_hash=row["ip_hash"],
            user_agent=row["user_agent"],
            browser=row["browser"],
            os=row["os"],
            device_type=row["device_type"],
            referer=row["referer"],
            referer_domain=row["referer_domain"],
            country=row["country"] if "country" in row.keys() else "Unknown",
        )


@dataclass
class LinkStats:
    """Aggregated analytics data for a shortened link."""

    link: Link
    total_clicks: int = 0
    unique_visitors: int = 0
    clicks_by_date: Dict[str, int] = field(default_factory=dict)
    clicks_by_hour: Dict[int, int] = field(default_factory=dict)
    top_referrers: List[Tuple[str, int]] = field(default_factory=list)
    browsers: Dict[str, int] = field(default_factory=dict)
    os_breakdown: Dict[str, int] = field(default_factory=dict)
    devices: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "link": self.link.to_dict(),
            "total_clicks": self.total_clicks,
            "unique_visitors": self.unique_visitors,
            "clicks_by_date": self.clicks_by_date,
            "clicks_by_hour": self.clicks_by_hour,
            "top_referrers": self.top_referrers,
            "browsers": self.browsers,
            "os_breakdown": self.os_breakdown,
            "devices": self.devices,
        }
