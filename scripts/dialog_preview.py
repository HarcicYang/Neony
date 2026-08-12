"""Render the file dialog under xvfb, screenshot it, then close it.

Usage: xvfb-run -a uv run python scripts/dialog_preview.py [kind]
Shows the dialog for 1.5s (auto-cancel), saving a screenshot to
/tmp/neony-dialog-<kind>.png — visual check only, no interaction.
"""

import subprocess
import sys
import tkinter as tk

from neony._dialog_worker import _FileDialog

kind = sys.argv[1] if len(sys.argv) > 1 else "open"

root = tk.Tk()
root.withdraw()
# _FileDialog blocks inside __init__ (wait_window), so the auto-close and
# screenshot callbacks must be scheduled on root beforehand.
root.after(700, lambda: subprocess.Popen(["import", "-window", "root", f"/tmp/neony-dialog-{kind}.png"]))
root.after(1500, root.destroy)
dialog = _FileDialog(root, kind, {"title": "Preview", "filetypes": [("Images", "*.png *.jpg"), ("All files", "*.*")]})
print("result:", repr(dialog.result))
