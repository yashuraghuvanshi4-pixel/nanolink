"""Database schema migration runner with version tracking."""

from __future__ import annotations

import sqlite3
from typing import Callable, List, Tuple

# Type definition for migration functions
MigrationFn = Callable[[sqlite3.Connection], None]


def migration_v1_baseline(conn: sqlite3.Connection) -> None:
    """Baseline schema: links and clicks tables with indices."""
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


def migration_v2_add_tags(conn: sqlite3.Connection) -> None:
    """Migration 2: Add tags column to links table for categorization."""
    cursor = conn.execute("PRAGMA table_info(links)")
    cols = [row[1] for row in cursor.fetchall()]
    if "tags" not in cols:
        conn.execute("ALTER TABLE links ADD COLUMN tags TEXT DEFAULT ''")


def migration_v3_add_metadata_indices(conn: sqlite3.Connection) -> None:
    """Migration 3: Index tags and expiration for faster queries."""
    conn.execute("CREATE INDEX IF NOT EXISTS idx_links_expires ON links(expires_at)")


MIGRATIONS: List[Tuple[int, str, MigrationFn]] = [
    (1, "baseline_schema", migration_v1_baseline),
    (2, "add_tags_column", migration_v2_add_tags),
    (3, "add_metadata_indices", migration_v3_add_metadata_indices),
]


class MigrationRunner:
    """Applies sequential schema migrations safely."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def get_current_version(self) -> int:
        """Fetch current database schema version from PRAGMA user_version."""
        cursor = self.conn.execute("PRAGMA user_version")
        row = cursor.fetchone()
        return row[0] if row else 0

    def apply_all(self) -> int:
        """Run all pending schema migrations."""
        current_version = self.get_current_version()

        for version, name, fn in MIGRATIONS:
            if version > current_version:
                with self.conn:
                    fn(self.conn)
                    self.conn.execute(f"PRAGMA user_version = {version}")
                current_version = version

        return current_version
