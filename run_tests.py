"""Runs every test and writes TEST_RESULTS.txt. Needs Python 3.9+ and `pip install lupa`;
PowerShell 7 (pwsh) for the companion tests, a C compiler for the native core test, and
clang + lld-link + llvm-dlltool for the DLL rebuild check (each is skipped when missing)."""
import io
import platform
import sys
import unittest
from datetime import datetime, timezone

if __name__ == "__main__":
    buf = io.StringIO()
    suite = unittest.defaultTestLoader.discover("tests", top_level_dir=".")
    result = unittest.TextTestRunner(stream=buf, verbosity=2).run(suite)
    head = (f"Rift Apart Randomizer dev 10.12 (build 10.0.8) - test run {datetime.now(timezone.utc):%Y-%m-%d %H:%M UTC}\n"
            f"Python {platform.python_version()} on {platform.system()}\n"
            f"ran {result.testsRun}, failures {len(result.failures)}, errors {len(result.errors)}, "
            f"skipped {len(result.skipped)}\n\n")
    text = head + buf.getvalue()
    with open("TEST_RESULTS.txt", "w", encoding="utf-8") as f:
        f.write(text)
    print(head.strip())
    sys.exit(0 if result.wasSuccessful() else 1)
