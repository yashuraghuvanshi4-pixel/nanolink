import os
import socket
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path

# Ensure root directory is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from nanolink import NanolinkClient, __version__
from nanolink.server.handler import NanolinkRequestHandler
from nanolink.storage.db import Database


def main():
    print("=" * 60)
    print("⚡ nanolink Comprehensive Verification & Smoke Suite")
    print("=" * 60)

    # 1. Run Unit & Integration Test Suite
    print("\n[1/4] Running Complete Test Suite...")
    loader = unittest.TestLoader()
    suite = loader.discover("tests")
    runner = unittest.TextTestRunner(verbosity=1)
    result = runner.run(suite)
    if not result.wasSuccessful():
        print("❌ Test suite failed!")
        return 1
    print("✔ All unit & integration tests passed!")

    # 2. Test CLI Invocations
    print("\n[2/4] Verifying CLI Commands (bulk, search, export, backup, vacuum)...")
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT)

    with tempfile.TemporaryDirectory() as tmp_dir:
        test_db = Path(tmp_dir) / "smoke.db"
        backup_db = Path(tmp_dir) / "backup.db"
        export_csv = Path(tmp_dir) / "export.csv"

        cli_tests = [
            ["python3", "-m", "nanolink.cli", "--version"],
            ["python3", "-m", "nanolink.cli", "--db", str(test_db), "shorten", "https://github.com", "--alias", "my-gh", "--json"],
            ["python3", "-m", "nanolink.cli", "--db", str(test_db), "search", "github", "--json"],
            ["python3", "-m", "nanolink.cli", "--db", str(test_db), "export", "my-gh", "-o", str(export_csv)],
            ["python3", "-m", "nanolink.cli", "--db", str(test_db), "backup", str(backup_db)],
            ["python3", "-m", "nanolink.cli", "--db", str(test_db), "vacuum"],
        ]
        for cmd in cli_tests:
            proc = subprocess.run(cmd, capture_output=True, text=True, env=env, cwd=str(REPO_ROOT))
            if proc.returncode != 0:
                print(f"❌ CLI command failed: {' '.join(cmd)}")
                print(proc.stderr)
                return 1

        if not backup_db.exists() or backup_db.stat().st_size == 0:
            print("❌ Backup file was not generated properly.")
            return 1
        if not export_csv.exists():
            print("❌ Export CSV was not created.")
            return 1

    print("✔ CLI commands passed validation!")

    # 3. Test Python SDK Client
    print("\n[3/4] Verifying Python SDK Client with live ephemeral server...")
    mem_db = Database(":memory:")
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()

    handler_cls = type("SmokeHandler", (NanolinkRequestHandler,), {"default_db": mem_db, "enable_logging": False})
    server = ThreadingHTTPServer(("127.0.0.1", port), handler_cls)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()

    try:
        client = NanolinkClient(base_url=f"http://127.0.0.1:{port}")
        health = client.health()
        assert health["status"] == "ok", "SDK health check failed"

        shortened = client.shorten("https://news.ycombinator.com", alias="hn-smoke", tags=["smoke", "news"])
        assert shortened["code"] == "hn-smoke", "SDK shorten failed"

        search_res = client.search("news")
        assert len(search_res.get("results", [])) > 0, "SDK search failed"

        stats = client.get_stats("hn-smoke")
        assert stats["link"]["code"] == "hn-smoke", "SDK stats failed"
        print("✔ Python SDK verified successfully!")
    finally:
        server.shutdown()
        server.server_close()

    # 4. Overall status
    print("\n[4/4] Overall Verification Status: HEALTHY 🚀 (All Systems Operational)")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
