#!/usr/bin/env python3
"""Build the standalone gallery executable with Nuitka (onefile).

Mirrors the Nuitka step in ``.github/workflows/packaging.yml``:

    1. sync dev deps + install Nuitka[onefile]
    2. build ``neony.gallery.__main__`` as a single-file executable
    3. rename the artifact to ``neony-gallery_<os>_<arch>_<version>_nuitka[.exe]``

The entry point is the source path ``src/neony/gallery/__main__.py``
(Nuitka takes a file, not a dotted module name); the rest of ``neony``
and its JS assets are pulled in via ``--include-package(-data)``.

Usage:
    python scripts/build_nuitka.py                  # sync + install + build + rename
    python scripts/build_nuitka.py --no-install     # skip uv sync / pip install
    python scripts/build_nuitka.py --output-dir dist  # move the artifact here
"""

from __future__ import annotations

import argparse
import platform
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _utf8_stdio() -> None:
    """Force UTF-8 on stdout/stderr.

    Windows consoles default to a narrow charset (cp1252) that cannot encode
    the box-drawing / ✓ decoration these scripts print — a print() would
    raise UnicodeEncodeError and fail the whole run.  GitHub Actions reads
    runner logs as UTF-8, so reconfiguring is safe on every platform.
    """
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")


_utf8_stdio()

# Shared with packaging.yml — keep the two in sync when flags change.
NUITKA_FLAGS = [
    "--onefile",
    "--assume-yes-for-downloads",
    "--include-package=neony.gallery",
    "--include-package-data=neony",
    "--include-module=lumiview.events",
    "--include-module=lumiview.task",
    "--include-module=lumiview.plugins.window_controls",
    "--output-filename=neony-gallery",
]

ENTRY = "src/neony/gallery/__main__.py"


def run(cmd: list[str]) -> int:
    print(f"$ {' '.join(cmd)}", flush=True)
    return subprocess.run(cmd, cwd=ROOT).returncode


def project_version() -> str:
    with (ROOT / "pyproject.toml").open("rb") as fh:
        return tomllib.load(fh)["project"]["version"]


def platform_label() -> str:
    """The ``<os>_<arch>`` half of the artifact name — same scheme as CI."""
    sys_name = platform.system().lower()
    machine = platform.machine().lower()
    if sys_name == "linux":
        return f"linux_{'x86_64' if machine in ('x86_64', 'amd64') else machine}"
    if sys_name == "windows":
        return "win_x86_64"
    if sys_name == "darwin":
        # Only arm64 wheels exist for the pinned webview deps (see packaging.yml).
        return "macos_arm64" if machine in ("arm64", "aarch64") else "macos_x86_64"
    return f"{sys_name}_{machine}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--no-install", action="store_true", help="skip uv sync + Nuitka[onefile] install")
    parser.add_argument("--output-dir", metavar="DIR", default=None, help="move the artifact into this directory")
    args = parser.parse_args()

    if not args.no_install:
        if run(["uv", "sync", "--group", "dev"]) != 0:
            return 1
        # Nuitka[onefile] pulls in zstandard — without it the onefile payload
        # is stored uncompressed (Linux 48 MB vs 13 MB with it).
        if run(["uv", "pip", "install", "nuitka[onefile]"]) != 0:
            return 1

    if run(["uv", "run", "python", "-m", "nuitka", *NUITKA_FLAGS, ENTRY]) != 0:
        return 1

    ext = ".exe" if sys.platform.startswith("win") else ""
    src = ROOT / f"neony-gallery{ext}"
    if not src.exists():
        print(f"✘ expected artifact not found: {src}", file=sys.stderr)
        return 1

    name = f"neony-gallery_{platform_label()}_{project_version()}_nuitka{ext}"
    dest = Path(args.output_dir) / name if args.output_dir else ROOT / name
    if args.output_dir:
        dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src), dest)
    print(f"\n✔ built {dest} ({dest.stat().st_size / 1024 / 1024:.1f} MiB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
