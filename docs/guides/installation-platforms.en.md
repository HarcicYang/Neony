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

The project develops and verifies primarily on Linux Wayland. The native WebView
binding links against the **WebKitGTK 4.1** API (GTK 3, libsoup 3), so every
distribution needs the package that provides `libwebkit2gtk-4.1.so.0`. Package
names differ across distributions; the commands below cover the common ones.

### Development dependencies

Debian and Ubuntu:

```bash
sudo apt-get update
sudo apt-get install -y libwebkit2gtk-4.1-dev libgtk-3-dev libxdo-dev
```

Fedora:

```bash
sudo dnf install -y webkit2gtk4.1-devel gtk3-devel libxdo-devel
```

Arch Linux:

```bash
sudo pacman -S --needed webkit2gtk-4.1 gtk3 xdotool
```

openSUSE:

```bash
sudo zypper install libwebkit2gtk-4_1-0-devel gtk3-devel libxdo-devel
```

> Each `-dev`/`-devel`/plain package above pulls in the matching WebKitGTK 4.1
> runtime, GTK 3, and libsoup 3 automatically through the dependency graph.

### Runtime dependencies for a packaged application

A packaged application needs the matching WebKitGTK **runtime** rather than the
compiler headers alone. Install only the runtime package on the target machine:

```text
Debian/Ubuntu : sudo apt-get install libwebkit2gtk-4.1-0
Fedora        : sudo dnf install webkit2gtk4.1
Arch Linux    : sudo pacman -S webkit2gtk-4.1
openSUSE      : sudo zypper install libwebkit2gtk-4_1-0
```

> Note for Arch users: the upstream packaging workflow previously documented
> `webkit2gtk-6.0`, but that provides the GTK 4 / newer API and is **not** the
> one this framework links. The framework targets the WebKitGTK 4.1 API, so
> install `webkit2gtk-4.1`.

### Optional system tray dependency

The native tray integration dynamically loads this library at runtime, so it is
optional rather than a hard link:

```text
Debian/Ubuntu : libayatana-appindicator3-1  (+ libayatana-appindicator3-dev for building)
Fedora        : libayatana-appindicator-gtk3
Arch Linux    : libayatana-appindicator
openSUSE      : libayatana-appindicator3-1
```

If it is unavailable, the windowed application still runs; tray creation is
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
