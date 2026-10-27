import sqlite3
import unittest
from nanolink.storage.migrations import MigrationRunner, MIGRATIONS


class TestMigrations(unittest.TestCase):
    def test_migration_runner_advances_version(self):
        conn = sqlite3.connect(":memory:")
        runner = MigrationRunner(conn)
        self.assertEqual(runner.get_current_version(), 0)

        final_version = runner.apply_all()
        self.assertEqual(final_version, len(MIGRATIONS))
        self.assertEqual(runner.get_current_version(), len(MIGRATIONS))

        # Check tables and columns exist
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        self.assertIn("links", tables)
        self.assertIn("clicks", tables)

        # Check tags column exists
        cursor = conn.execute("PRAGMA table_info(links)")
        cols = [row[1] for row in cursor.fetchall()]
        self.assertIn("tags", cols)

    def test_migration_runner_idempotent(self):
        conn = sqlite3.connect(":memory:")
        runner = MigrationRunner(conn)
        runner.apply_all()
        # Second run should not fail or re-apply
        v2 = runner.apply_all()
        self.assertEqual(v2, len(MIGRATIONS))


if __name__ == "__main__":
    unittest.main()
