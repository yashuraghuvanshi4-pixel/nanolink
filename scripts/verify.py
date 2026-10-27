import os
from pathlib import Path
import subprocess
import sys
import unittest

# Ensure root directory is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

def main():
    print("=" * 60)
    print("⚡ nanolink End-to-End Verification Suite")
    print("=" * 60)

    # 1. Run Unit & Integration Test Suite
    print("\n[1/3] Running Python Test Suite...")
    loader = unittest.TestLoader()
    suite = loader.discover("tests")
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    if not result.wasSuccessful():
        print("❌ Test suite failed!")
        return 1
    print("✔ All unit & integration tests passed!")

    # 2. Test CLI invocations
    print("\n[2/3] Verifying CLI functionality...")
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT)
    cli_tests = [
        ["python3", "-m", "nanolink.cli", "--version"],
        ["python3", "-m", "nanolink.cli", "--db", ":memory:", "shorten", "https://github.com", "--alias", "my-gh", "--json"],
        ["python3", "-m", "nanolink.cli", "--db", ":memory:", "list", "--json"],
    ]
    for cmd in cli_tests:
        proc = subprocess.run(cmd, capture_output=True, text=True, env=env, cwd=str(REPO_ROOT))
        if proc.returncode != 0:
            print(f"❌ CLI command failed: {' '.join(cmd)}")
            print(proc.stderr)
            return 1
    print("✔ CLI verified successfully!")

    # 3. Overall status
    print("\n[3/3] Overall Verification Status: HEALTHY 🚀")
    print("=" * 60)
    return 0

if __name__ == "__main__":
    sys.exit(main())
