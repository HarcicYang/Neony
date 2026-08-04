"""Demo smoke test — every ``demo_*.py`` must start and reach the LumiView
event loop without crashing.

Each demo is spawned as a subprocess (a real window opens, so this runs
under ``xvfb-run`` in CI), allowed ~6s to import, build its page tree and
enter the blocking event loop, then SIGTERM'd.  An early exit with a
non-zero code means the demo crashed during startup — the captured
stderr is reported so the traceback is visible in the test output.

Marked ``smoke``: excluded from the default pytest run (``-m 'not smoke'``
in pyproject.toml), because real windows would pop up on any display.
Run explicitly under a virtual display — on Wayland sessions this must
be xvfb-run, otherwise the demos would open on your real desktop::

    xvfb-run --auto-servernum uv run pytest tests/smoke_demos.py -m smoke
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.smoke

ROOT = Path(__file__).resolve().parent.parent
DEMOS = sorted(ROOT.glob("demo_*.py"))

# How long a demo may keep running before we consider it "started".
# Startup is import + tree build + window creation — a few seconds is
# plenty on CI; anything faster is a crash, anything slower is a hang
# that the per-test timeout catches.
STARTUP_GRACE = 6.0


@pytest.mark.parametrize("demo_path", DEMOS, ids=lambda p: p.name)
def test_demo_starts(demo_path: Path) -> None:
    """Spawn the demo; it must still be alive after the grace period."""
    env = os.environ.copy()
    if sys.platform == "linux" and os.environ.get("DISPLAY"):
        # ``xvfb-run`` only sets DISPLAY (X11) — a live Wayland session
        # still wins via WAYLAND_DISPLAY, and GTK would then pop windows
        # on the user's desktop instead of the virtual display.  Pin the
        # X11 backend so demos render into whatever DISPLAY points to.
        env["WAYLAND_DISPLAY"] = ""
        env["GDK_BACKEND"] = "x11"
    proc = subprocess.Popen(
        [sys.executable, str(demo_path)],
        cwd=ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        try:
            exit_code = proc.wait(timeout=STARTUP_GRACE)
        except subprocess.TimeoutExpired:
            # Still running → it reached the event loop.  Success.
            return
        # Exited early: a crash during import/build/window creation.
        stdout, stderr = proc.communicate(timeout=2)
        pytest.fail(
            f"{demo_path.name} exited during startup (code {exit_code}).\n"
            f"--- stdout (last 1000 chars) ---\n{stdout[-1000:]}\n"
            f"--- stderr (last 2000 chars) ---\n{stderr[-2000:]}"
        )
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
