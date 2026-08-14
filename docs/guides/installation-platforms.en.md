# Installation and platforms

> [中文版本](installation-platforms.zh.md) · [Getting started](../getting-started.en.md) · [Documentation home](../README.en.md)

Neony renders Python-built DOM trees inside a native WebView. Installing the
Python package is necessary but not always sufficient: the WebView and some
optional desktop integrations are supplied by the operating system.

## Python environments

For an application installed from the package index:

```bash
python -m pip install neony
```

For a checkout of this repository:

```bash
uv sync --group dev
```

The repository's recommended commands use `uv run`, for example:

```bash
uv run gallery
uv run python scripts/check_all.py
```

`package.json` is only for the JavaScript runtime tests. A clean checkout has
no tracked `node_modules/`; `scripts/check_all.py` runs `npm ci` automatically
when the directory is absent.

## Linux

The project develops and verifies primarily on Linux Wayland. Debian/Ubuntu CI
uses these development packages:

```bash
sudo apt-get update
sudo apt-get install -y libwebkit2gtk-4.1-dev libgtk-3-dev libxdo-dev
```

A packaged application needs the matching WebKitGTK runtime rather than the
compiler headers alone. The exact package name depends on the distribution;
install the WebKitGTK 4.1 runtime corresponding to the development package.

The native tray integration additionally needs:

```text
libayatana-appindicator
```

If it is unavailable, the windowed application can still run; tray creation is
logged and skipped by the application layer.

### Wayland, X11, and CI

Wayland is the primary Linux desktop verification target. The Linux blur path
uses the compositor's background-effect protocol where supported; positioning
is also subject to Wayland restrictions.

X11 is not a complete support target at this stage. CI uses `xvfb-run` for
headless startup smoke tests, which proves that demos reach the event loop but
does not prove every X11 desktop behavior or rendering result.

## Windows

Windows uses the operating system's WebView2 runtime. Install or enable the
WebView2 runtime before running an application. Native window materials such
as Acrylic and Mica depend on the platform and window configuration.

The project has Windows packaging support in the Nuitka workflow, but individual
features should still be verified on the target Windows version before shipping.

## macOS

macOS uses WKWebView supplied by the system. File dialogs use `osascript` and
transparent windows can request a native blur effect. WKWebView does not expose
all filesystem metadata in a web drop event, so applications that depend on
file paths should use the Neony native drop channel and test on the target OS.

The macOS runtime and HiDPI/mixed-DPI behavior are not fully covered by the
repository's Linux CI; treat those as platform-specific verification work.

## Native file dialogs

The public async methods are:

```python
path = await app.open_file()
paths = await app.open_files()
destination = await app.save_file(default_name="output.txt")
folder = await app.select_folder()
```

The worker selects the platform implementation:

```text
Linux   → zenity when available, otherwise tkinter
macOS   → osascript
Windows → PowerShell
Other   → tkinter fallback
```

The call runs in an executor thread, so the application's asyncio loop can keep
serving other work while the picker is open. A cancelled single-selection call
returns `None`; a cancelled multi-selection call returns `[]`. File filters are
passed as `(label, pattern)` pairs, for example:

```python
filetypes = [("PNG images", "*.png"), ("All files", "*.*")]
```

If a platform command or fallback cannot open, the public API normalizes the
usual failure/cancel result to the same empty shape. Test picker behavior on the
platform where the application will ship.

## Common symptoms

| Symptom | First checks |
| --- | --- |
| WebView fails to start on Linux | Confirm the WebKitGTK runtime and GTK libraries are installed; check the process stderr. |
| Tray icon is missing | Install `libayatana-appindicator`; tray creation is optional and may be skipped. |
| File picker does not appear | Check `zenity`/`osascript`/PowerShell or tkinter, plus the display/session environment. |
| A demo exits immediately in CI | Run it under `xvfb-run`; use `tests/smoke_demos.py` rather than opening a real desktop window in a static check. |
| A transparent window has no blur | Check compositor/platform support; blur failure is non-fatal and leaves the window usable. |

For a first working application, return to
[Getting started](../getting-started.en.md). For exact configuration fields,
see the [API reference](../api.en.md).
