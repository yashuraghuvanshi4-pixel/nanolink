"""SQLite database storage engine with connection pooling and WAL mode."""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional
from nanolink.models import Link, ClickEvent

DEFAULT_DB_PATH = Path.home() / ".nanolink" / "nanolink.db"


class Database:
    """Manages SQLite connection, schema migrations, and queries."""

    def __init__(self, db_path: Optional[str | Path] = None) -> None:
        self._is_memory = False
        self._shared_memory_conn: Optional[sqlite3.Connection] = None

        if db_path is None or str(db_path) == "":
            self.db_path = DEFAULT_DB_PATH
        elif str(db_path) == ":memory:":
            self._is_memory = True
            self.db_path = ":memory:"
        else:
            self.db_path = Path(db_path)

        if not self._is_memory:
            os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)
        else:
            # For in-memory database, maintain a persistent connection
            self._shared_memory_conn = sqlite3.connect(
                ":memory:", check_same_thread=False, timeout=10.0
            )
            self._shared_memory_conn.row_factory = sqlite3.Row
            self._shared_memory_conn.execute("PRAGMA foreign_keys = ON;")

        self._init_db()

    def get_connection(self) -> sqlite3.Connection:
        """Create or return a configured SQLite connection."""
        if self._is_memory and self._shared_memory_conn is not None:
            return self._shared_memory_conn

        conn = sqlite3.connect(
            str(self.db_path),
            check_same_thread=False,
            timeout=10.0,
        )
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA synchronous = NORMAL;")
        return conn

    def _init_db(self) -> None:
        """Initialize database schema with indexed tables."""
        conn = self.get_connection()
        try:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS links (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code TEXT NOT NULL UNIQUE,
                    target_url TEXT NOT NULL,
                    title TEXT,
                    created_at TEXT NOT NULL,
                    expires_at TEXT,
                    max_clicks INTEGER,
                    click_count INTEGER DEFAULT 0,
                    is_active INTEGER DEFAULT 1
                );

                CREATE INDEX IF NOT EXISTS idx_links_code ON links(code);
                CREATE INDEX IF NOT EXISTS idx_links_created ON links(created_at DESC);

                CREATE TABLE IF NOT EXISTS clicks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    link_code TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    ip_hash TEXT NOT NULL,
                    user_agent TEXT,
                    browser TEXT,
                    os TEXT,
                    device_type TEXT,
                    referer TEXT,
                    referer_domain TEXT,
                    country TEXT,
                    FOREIGN KEY (link_code) REFERENCES links(code) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_clicks_code_ts ON clicks(link_code, timestamp DESC);
                CREATE INDEX IF NOT EXISTS idx_clicks_ip ON clicks(ip_hash);
                """
            )
            conn.commit()
        finally:
            if not self._is_memory:
                conn.close()

    def save_link(self, link: Link) -> Link:
        """Insert a short link record."""
        conn = self.get_connection()
        try:
            cursor = conn.execute(
                """
                INSERT INTO links (code, target_url, title, created_at, expires_at, max_clicks, click_count, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    link.code,
                    link.target_url,
                    link.title,
                    link.created_at,
                    link.expires_at,
                    link.max_clicks,
                    link.click_count,
                    1 if link.is_active else 0,
                ),
            )
            conn.commit()
            link.id = cursor.lastrowid
            return link
        finally:
            if not self._is_memory:
                conn.close()

    def get_link(self, code: str) -> Optional[Link]:
        """Fetch link by unique short code."""
        conn = self.get_connection()
        try:
            row = conn.execute(
                "SELECT * FROM links WHERE code = ? AND is_active = 1", (code,)
            ).fetchone()
            if row:
                return Link.from_row(row)
            return None
        finally:
            if not self._is_memory:
                conn.close()

    def increment_clicks(self, code: str) -> int:
        """Atomically increment click count for a short link."""
        conn = self.get_connection()
        try:
            cursor = conn.execute(
                "UPDATE links SET click_count = click_count + 1 WHERE code = ?", (code,)
            )
            conn.commit()
            if cursor.rowcount == 0:
                return 0
            row = conn.execute(
                "SELECT click_count FROM links WHERE code = ?", (code,)
            ).fetchone()
            return row["click_count"] if row else 0
        finally:
            if not self._is_memory:
                conn.close()

    def delete_link(self, code: str) -> bool:
        """Permanently delete a short link and its click cascade."""
        conn = self.get_connection()
        try:
            cursor = conn.execute("DELETE FROM links WHERE code = ?", (code,))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            if not self._is_memory:
                conn.close()

    def list_links(self, limit: int = 50, offset: int = 0) -> List[Link]:
        """List shortened links in reverse chronological order."""
        conn = self.get_connection()
        try:
            rows = conn.execute(
                "SELECT * FROM links ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (limit, offset),
            ).fetchall()
            return [Link.from_row(r) for r in rows]
        finally:
            if not self._is_memory:
                conn.close()

    def record_click(self, event: ClickEvent) -> ClickEvent:
        """Record an analytics click event."""
        conn = self.get_connection()
        try:
            cursor = conn.execute(
                """
                INSERT INTO clicks (
                    link_code, timestamp, ip_hash, user_agent, browser,
                    os, device_type, referer, referer_domain, country
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.link_code,
                    event.timestamp,
                    event.ip_hash,
                    event.user_agent,
                    event.browser,
                    event.os,
                    event.device_type,
                    event.referer,
                    event.referer_domain,
                    event.country,
                ),
            )
            conn.commit()
            event.id = cursor.lastrowid
            return event
        finally:
            if not self._is_memory:
                conn.close()

    def get_clicks_for_link(self, code: str, limit: int = 1000) -> List[ClickEvent]:
        """Retrieve recent click events for a specific link."""
        conn = self.get_connection()
        try:
            rows = conn.execute(
                "SELECT * FROM clicks WHERE link_code = ? ORDER BY timestamp DESC LIMIT ?",
                (code, limit),
            ).fetchall()
            return [ClickEvent.from_row(r) for r in rows]
        finally:
            if not self._is_memory:
                conn.close()

    def get_global_metrics(self) -> Dict[str, Any]:
        """Get aggregate metrics across the entire database."""
        conn = self.get_connection()
        try:
            total_links = conn.execute("SELECT COUNT(*) as c FROM links").fetchone()["c"]
            total_clicks = conn.execute("SELECT COUNT(*) as c FROM clicks").fetchone()["c"]
            return {
                "total_links": total_links,
                "total_clicks": total_clicks,
            }
        finally:
            if not self._is_memory:
                conn.close()
