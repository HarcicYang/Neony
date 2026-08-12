#!/usr/bin/env python3
"""Run the full project check suite in one pass and summarize the results.

Mirrors the checks in ``.github/workflows/ci.yml``:

    ruff check .          ruff format --check .
    pyrefly check
    pytest -v --tb=short        (smoke tests excluded by default)
    npm test                     (vitest + jsdom)

Each tool streams its output live so long-running steps (pytest, vitest)
stay visible; the script ends with a one-screen summary table and a
non-zero exit code if any check failed — usable as a CI entry point too.

``uv run`` syncs the project's dev dependency group as needed, so a
stale/absent venv self-heals instead of failing with "command not found".

Options:
    --fix      run ``ruff check --fix`` + ``ruff format`` first, then check
    --smoke    also run the display-requiring demo smoke tests under
               xvfb-run (Linux only; skipped with a warning if unavailable)
    --list     print the checks that would run, then exit
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


@dataclass
class Check:
    name: str
    cmd: list[str]
    dur: float = 0.0
    rc: int | None = None


def make_checks(*, smoke: bool) -> list[Check]:
    checks = [
        Check("ruff check", ["uv", "run", "ruff", "check", "."]),
        Check("ruff format", ["uv", "run", "ruff", "format", "--check", "."]),
        Check("pyrefly", ["uv", "run", "pyrefly", "check"]),
        Check("pytest", ["uv", "run", "pytest", "-v", "--tb=short"]),
    ]
    # JS tests need vitest's node_modules.  A clean CI checkout has none —
    # bootstrap with ``npm ci`` first; local dev already has it installed.
    if (ROOT / "node_modules").is_dir():
        checks.append(Check("JS tests (vitest)", ["npm", "test"]))
    else:
        checks.append(Check("JS install (npm ci)", ["npm", "ci"]))
        checks.append(Check("JS tests (vitest)", ["npm", "test"]))
    if smoke:
        if shutil.which("xvfb-run"):
            checks.append(
                Check(
                    "smoke demos (xvfb)",
                    [
                        "xvfb-run",
                        "--auto-servernum",
                        "uv",
                        "run",
                        "pytest",
                        "tests/smoke_demos.py",
                        "-v",
                        "-m",
                        "smoke",
                    ],
                )
            )
        else:
            print("⚠ xvfb-run not found — skipping smoke demos (they need a display)", file=sys.stderr)
    return checks


def run_check(check: Check) -> None:
    print(f"\n▶ {check.name}")
    print(f"  $ {' '.join(check.cmd)}")
    start = time.monotonic()
    try:
        proc = subprocess.run(check.cmd, cwd=ROOT)
        check.rc = proc.returncode
    except FileNotFoundError:
        # A missing executable (e.g. npm not on PATH) must fail the run
        # with a clean non-zero code — not a traceback that aborts the
        # suite mid-way and hides the summary table.
        print(f"✘ command not found on PATH: {check.cmd[0]}", file=sys.stderr)
        check.rc = 127
    check.dur = time.monotonic() - start


def print_summary(checks: list[Check]) -> list[Check]:
    width = max(len(c.name) for c in checks) + 2
    print("\n" + "─" * (width + 44))
    print(f"{'CHECK':<{width}}{'RESULT':<10}{'TIME':<10}STATUS")
    print("─" * (width + 44))
    for c in checks:
        ok = c.rc == 0
        status = "PASS" if ok else ("SKIP" if c.rc is None else "FAIL")
        print(f"{c.name:<{width}}{status:<10}{c.dur:>6.1f}s   {'✔' if ok else '✘'}")
    print("─" * (width + 44))
    failed = [c for c in checks if c.rc not in (None, 0)]
    total = len(checks)
    passed = total - len(failed)
    if failed:
        print(f"{passed}/{total} checks passed — failing: {', '.join(c.name for c in failed)}")
        print("Run the failing command above to see the full error output.")
    else:
        print(f"All {total} checks passed.")
    return failed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--fix", action="store_true", help="apply ruff auto-fixes before checking")
    parser.add_argument("--smoke", action="store_true", help="also run xvfb smoke tests")
    parser.add_argument("--list", action="store_true", help="print the checks that would run, then exit")
    args = parser.parse_args()

    if args.fix:
        print("$ uv run ruff check . --fix")
        subprocess.run(["uv", "run", "ruff", "check", ".", "--fix"], cwd=ROOT)
        print("$ uv run ruff format .")
        subprocess.run(["uv", "run", "ruff", "format", "."], cwd=ROOT)
        print()

    checks = make_checks(smoke=args.smoke)
    if args.list:
        for c in checks:
            print(f"  {c.name:20} $ {' '.join(c.cmd)}")
        return 0

    for missing in (t for t in ("uv", "npm") if shutil.which(t) is None):
        print(f"✘ required tool not found on PATH: {missing}", file=sys.stderr)
        return 2

    for c in checks:
        run_check(c)

    failed = print_summary(checks)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
