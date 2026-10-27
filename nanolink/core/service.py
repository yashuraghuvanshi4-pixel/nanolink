"""Link business logic service with validation, TTL, and collision resolution."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import List, Optional, Set
from nanolink.models import Link, validate_url, validate_alias
from nanolink.core.base62 import generate_code_from_hash, generate_random_code
from nanolink.storage.db import Database

RESERVED_CODES: Set[str] = {
    "api",
    "static",
    "dashboard",
    "stats",
    "health",
    "qr",
    "favicon.ico",
    "robots.txt",
    "metrics",
}


class LinkServiceError(Exception):
    """Base exception for LinkService errors."""


class InvalidURLError(LinkServiceError):
    """Raised when the target URL fails validation."""


class InvalidAliasError(LinkServiceError):
    """Raised when a custom alias is malformed or reserved."""


class AliasAlreadyExistsError(LinkServiceError):
    """Raised when a custom alias is already occupied."""


class LinkNotFoundError(LinkServiceError):
    """Raised when a requested short code is not found."""


class LinkExpiredError(LinkServiceError):
    """Raised when a short link has exceeded its expiration time or max clicks."""


class LinkService:
    """Coordinates link shortening, resolution, expiry, and lifecycle management."""

    def __init__(self, db: Optional[Database] = None) -> None:
        self.db = db or Database()

    def shorten(
        self,
        url: str,
        custom_alias: Optional[str] = None,
        title: Optional[str] = None,
        ttl_seconds: Optional[int] = None,
        max_clicks: Optional[int] = None,
        tags: Optional[List[str]] = None,
    ) -> Link:
        """Create a shortened link with optional alias, TTL, click cap, and tags."""
        # Normalize and validate URL
        target_url = url.strip()
        if not validate_url(target_url):
            raise InvalidURLError(f"Invalid URL: '{url}'")

        expires_at: Optional[str] = None
        if ttl_seconds is not None and ttl_seconds > 0:
            exp_time = datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)
            expires_at = exp_time.isoformat()

        if custom_alias:
            alias = custom_alias.strip()
            if not validate_alias(alias):
                raise InvalidAliasError(
                    f"Invalid custom alias '{alias}'. Must be 3-64 chars [a-zA-Z0-9_-]."
                )
            if alias.lower() in RESERVED_CODES:
                raise InvalidAliasError(f"Alias '{alias}' is a reserved system path.")

            existing = self.db.get_link(alias)
            if existing is not None:
                raise AliasAlreadyExistsError(f"Short code '{alias}' is already in use.")
            code = alias
        else:
            code = self._generate_unique_code(target_url)

        cleaned_tags = [t.strip().lower() for t in (tags or []) if t.strip()]

        link = Link(
            code=code,
            target_url=target_url,
            title=title.strip() if title else None,
            expires_at=expires_at,
            max_clicks=max_clicks,
            tags=cleaned_tags,
        )
        return self.db.save_link(link)

    def _generate_unique_code(self, target_url: str) -> str:
        """Generate a unique short code with deterministic hash & collision retries."""
        # Try deterministic hash with up to 5 collision salts
        for attempt in range(5):
            salt = f"attempt_{attempt}" if attempt > 0 else ""
            candidate = generate_code_from_hash(target_url, length=7, salt=salt)
            if candidate.lower() in RESERVED_CODES:
                continue
            existing = self.db.get_link(candidate)
            if existing is None:
                return candidate
            if existing.target_url == target_url and not existing.is_expired():
                # Idempotent return for identical URL
                return candidate

        # Fallback to cryptographically random code
        for _ in range(10):
            candidate = generate_random_code(length=7)
            if candidate.lower() in RESERVED_CODES:
                continue
            if self.db.get_link(candidate) is None:
                return candidate

        raise LinkServiceError("Failed to generate a unique short code after 15 attempts.")

    def resolve(self, code: str) -> Link:
        """Resolve a short code to its destination link.

        Args:
            code: The short link identifier.

        Returns:
            The active Link object.

        Raises:
            LinkNotFoundError: If code is not found.
            LinkExpiredError: If link has expired.
        """
        link = self.db.get_link(code)
        if link is None:
            raise LinkNotFoundError(f"Short code '{code}' not found.")

        if link.is_expired():
            raise LinkExpiredError(f"Short link '{code}' has expired.")

        return link

    def delete(self, code: str) -> bool:
        """Delete a short link."""
        return self.db.delete_link(code)

    def list_links(self, limit: int = 50, offset: int = 0, tag: Optional[str] = None) -> List[Link]:
        """List shortened links with optional tag filter."""
        return self.db.list_links(limit=limit, offset=offset, tag=tag)

    def bulk_shorten(self, items: List[dict]) -> List[dict]:
        """Shorten multiple URLs in batch.

        Args:
            items: List of dictionaries with url, optional alias, title, ttl_seconds, max_clicks.

        Returns:
            List of result dictionaries with success status, code, and short_url or error message.
        """
        results = []
        for item in items:
            url = item.get("url")
            alias = item.get("alias")
            title = item.get("title")
            ttl_seconds = item.get("ttl_seconds")
            max_clicks = item.get("max_clicks")

            try:
                link = self.shorten(
                    url=url,
                    custom_alias=alias,
                    title=title,
                    ttl_seconds=ttl_seconds,
                    max_clicks=max_clicks,
                )
                res = link.to_dict()
                res["success"] = True
                results.append(res)
            except Exception as err:
                results.append({
                    "success": False,
                    "url": url,
                    "error": str(err),
                })
        return results
