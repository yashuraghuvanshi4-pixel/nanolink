"""Unit tests for SQLite hot backup and vacuum maintenance."""

import tempfile
import unittest
from pathlib import Path
from nanolink.cli import main
from nanolink.core.service import LinkService
from nanolink.storage.db import Database


class TestBackupAndVacuum(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "source.db"
        self.db = Database(self.db_path)
        self.service = LinkService(self.db)
        self.service.shorten("https://example.com/test", custom_alias="test-backup")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_database_backup_creates_identical_copy(self):
        backup_path = Path(self.temp_dir.name) / "backup.db"
        self.db.backup(backup_path)

        self.assertTrue(backup_path.exists())
        self.assertGreater(backup_path.stat().st_size, 0)

        # Verify backup database contains the link
        backup_db = Database(backup_path)
        link = backup_db.get_link("test-backup")
        self.assertIsNotNone(link)
        self.assertEqual(link.target_url, "https://example.com/test")

    def test_database_vacuum(self):
        # Insert and delete links to create fragmented space
        for i in range(10):
            self.service.shorten(f"https://example.com/junk/{i}")
        self.db.vacuum()
        self.assertGreater(self.db.get_db_size(), 0)

    def test_cli_backup_command(self):
        backup_file = Path(self.temp_dir.name) / "cli_backup.db"
        code = main(["--db", str(self.db_path), "backup", str(backup_file)])
        self.assertEqual(code, 0)
        self.assertTrue(backup_file.exists())

    def test_cli_vacuum_command(self):
        code = main(["--db", str(self.db_path), "vacuum"])
        self.assertEqual(code, 0)


if __name__ == "__main__":
    unittest.main()
