# Core API

> [中文版本](core.zh.md) · [API index](README.en.md) · [Documentation home](../README.en.md)

The application object, entry points, and window lifecycle. Import from
`neony.application`.

## `NeonApplication`

The application object — owns the window, the bridge, the theme, and
shared state. Construct with a `Config`, build a `Page`, then `run()`.

```python
from neony.application import Config, NeonApplication, Page, Theme, WebViewConfig, WindowConfig

app = NeonApplication(
    Config(
        window=WindowConfig(title="Demo", width=480, height=360),
        webview=WebViewConfig(devtools=True),
    )
)
app.state.count = 0  # shared mutable state
app.theme = Theme.get("light")  # pick the initial preset before run()


def main() -> None:
    app.run(page)
```

**Typed state:** `state` defaults to a bare `SimpleNamespace`. Pass any
object — a `dataclass`, pydantic model, or plain class — via the `state=`
argument to get typed attribute access and IDE completion:

```python
from dataclasses import dataclass


@dataclass
class AppState:
    count: int = 0
    user_name: str = ""


app = NeonApplication(Config(...), state=AppState())
app.state.count += 1  # typed as int
app.state.user_name = "Ada"
```

All windows share the same `state` object, so this is the imperative
counterpart to [`SharedSignal`](reactive.en.md#sharedsignal) for cross-window data.

**Attributes:** `config`, `state`, `theme`, `ready_handler`, `close_handler`

**Window methods** (all async):

`set_title(title)`, `set_size(w, h)`, `minimize()`, `toggle_maximize()`,
`is_maximized()`, `set_fullscreen(f)`, `start_dragging()`, `close()`,
`apply_blur(color?)`, `apply_acrylic(color?)`, `apply_mica()`,
`clear_effect(effect)`, `eval_js(script)`, `set_icon(icon)`.

`transparent=True` already applies the platform material automatically
(Wayland blur on Linux where supported, Acrylic on Windows, Blur on
macOS). The `apply_*` methods are manual overrides and platform-limited:
`apply_blur` is macOS/Windows; acrylic / mica are Windows 11.

**App methods:** `exit(code=0)` — graceful app shutdown (sync). With
`close_to_tray=True` window closes hide the app instead of quitting, so
`exit()` is the way out — e.g. a tray "Quit" menu item.

**Theme / rendering:**

`set_theme(theme)`, `sync_theme()`, `set_background(url)`, `render()`

**File dialogs** (all async — system-native):
`open_file(...) -> str | None`, `open_files(...) -> list[str]`,
`save_file(...) -> str | None`, `select_folder(...) -> str | None`.

Cancelling returns `None` (or `[]` for the multi-select); a dialog that
can't be shown also returns `None` — never an exception.

```python
path = await app.open_file(
    title="Open image", default_dir="~/Pictures", filetypes=[("PNG images", "*.png"), ("All files", "*.*")]
)
if path is None:
    return  # cancelled
paths = await app.open_files(...)  # [] on cancel
dest = await app.save_file(default_name="out.txt")  # str | None
folder = await app.select_folder()  # str | None
```

The dialogs are the platform's own — zenity on Linux (most desktops
ship it), `osascript` on macOS, PowerShell on Windows, with a tkinter
fallback — shown as a child process so the app's event loop keeps
running while they're up. Nothing is drawn by Neony itself: the
look, navigation and filters are exactly what the OS provides.

`filetypes` maps onto the native filter UI (`[("PNG images", "*.png"),
("All files", "*.*")]`); `default_dir` / `default_name` preselect the
starting location. No WebView, no tkinter window in-process, no
bundled dialog component.

## `launch()`

One-liner entry point — builds a `Config` from keyword arguments.

```python
from neony.application import Page, launch

launch(page, title="Demo", width=480, height=360, devtools=True)
```

Accepts all `WindowConfig` / `WebViewConfig` fields plus
`mount_selector`, `auto_render`, and `state` (a custom state object —
see [`NeonApplication`](#neonapplication)).

## `Config`, `WindowConfig`, `WebViewConfig`

Pydantic config models. `WindowConfig` covers geometry and appearance
(`title`, `width`, `height`, `decorations`, `transparent`,
`always_on_top`, `resizable`, `icon`, …). `WebViewConfig` covers runtime
options (`devtools`, `incognito`, `user_agent`, `javascript`, …).

**`WindowConfig.icon`** — file path (PNG, ICO, …) or raw RGBA data
`(bytes, width, height)`, shown in the OS window chrome of *decorated*
windows. Frameless windows have no OS chrome — see the
[`TitleBar`](layout-chrome.en.md#titlebar) `icon` parameter for inline icons, and
[`NeonApplication.set_icon()`](#neonapplication) to swap at runtime.

**`WebViewConfig.default_context_menus`** — off by default: the app
draws its own menus (the `Menu` component, `contextmenu` events) and
the webview's native right-click menu would cover them. Set `True` for
the platform default menu.

## `Page`

Top-level flex-column container. Two layers: a full-viewport backdrop
and a width-constrained, centered content column.

```python
Page(gap="16px", padding="24px", max_width="720px")
Page(fill=True, radius="12px")  # chrome layouts
```

**Options:** `direction`, `gap`, `padding`, `align`, `justify`,
`width`, `max_width`, `glass`, `fill`, `radius`

`fill=True` stretches to the full window height. `radius` rounds the
window frame (for transparent frameless windows).

**Methods:** `add(child)` (chainable), `on_close(fn)` (chainable —
see [Lifecycle](#lifecycle)), `build()` → DOMElement

## Lifecycle

Startup and teardown are declared as plain attributes — the framework
owns the wiring to the native window events.

```python
async def on_ready() -> None:
    print("windows are up")


async def on_shutdown() -> None:
    save_state(app.state)  # runs after all windows close


app.ready_handler = on_ready
app.close_handler = on_shutdown
```

`close_handler` runs exactly once, after the last window closes and
before the event loop stops — the last chance for async cleanup.

**Per-window close** — `Page.on_close(fn)` (sync or async, chainable,
multiple handlers stack). Fires when that page's window is closing,
before it actually closes; exceptions are logged and never block the
close. For a confirm-before-close dialog, take over the titlebar close
button instead — see [`TitleBar.override_close`](layout-chrome.en.md#titlebar).

```python
page = Page()
page.on_close(lambda: print("window closing"))
```

**Focus tracking** — `Page.on_focus(fn)` / `Page.on_blur(fn)` (sync or
async, chainable, multiple handlers stack) fire when the page's window
gains / loses keyboard focus — useful for pausing timers, updating a
status bar, or knowing which window is active in a multi-window app.

```python
page = Page()
page.on_focus(lambda: print("active"))
page.on_blur(lambda: print("inactive"))
```

## Multi-window

`run()` accepts several pages — each opens its own window. All windows
share one event loop and the app's `state` namespace; an event handler
only re-renders the window it came from.

```python
app = NeonApplication(Config(...))
app.run(page_one, page_two)


async def on_ready() -> None:
    await app.set_title("Counter", window_index=0)
    await app.set_title("Display", window_index=1)


app.ready_handler = on_ready
```

Every window-control method takes `window_index` (default 0).

`launch([page_one, page_two], ...)` accepts a list too.

## Navigation policies

A link or redirect inside the page would otherwise navigate the webview
away from your UI. Neony installs safe defaults on every window —
navigation blocked, new-window requests denied, downloads cancelled —
so nothing can escape without your say-so. Override them per-page.

**Decision policies** — a single handler, the last one registered wins
(a decision can't be merged):

```python
# Allow only your own site; everything else is blocked.
page.on_navigation(lambda url: url.startswith("https://myapp.example"))

# target="_blank" links and window.open(): "allow" or "deny".
page.on_new_window(lambda url: "deny")

# Return True to allow, False to cancel, or a path to redirect the
# download to a custom location.
page.on_download_started(lambda url, path: "/downloads/")
```

**Notifications** — multiple handlers stack, all run:

```python
# url, final path (or None if cancelled), success flag.
page.on_download_completed(lambda url, path, ok: print(f"downloaded {path}"))
```

## `Tray` & `TrayItem` — system tray (native menu)

A tray icon with a native context menu, backed by lumiview .dev4
(muda menus + TrayIcon). Assign `app.tray` before `run()`; the icon
materializes once the app is up.

```python
from neony.application import Tray, TrayItem

app.tray = Tray(
    icon="tray.png",  # file path or raw RGBA (bytes, width, height)
    tooltip="My App",
    items=[
        TrayItem("Show Window", id="show", on_activate=show_handler),
        TrayItem.separator(),
        TrayItem("Quit", id="quit", accelerator="CmdOrCtrl+Q", on_activate=quit_handler),
    ],
    menu_on_left_click=False,  # free the left button for on_left_click
    on_left_click=toggle_handler,  # sync or async
    close_to_tray=True,  # close hides the app instead of quitting
)
```

- `TrayItem` — `text`, optional `id` (carried by activation
  callbacks), `accelerator` (muda syntax; Windows may not fire it from
  the keyboard), `on_activate` (sync or async, run on the asyncio
  loop), `checked=True` for a check item; `TrayItem.separator()` for a
  divider.
- `close_to_tray=True` — every window's close request is prevented and
  the app hides (restore from the menu / tray click; on macOS a Dock
  click via `ReopenEvent`). `Page.on_close` handlers still run.
- `on_left_click` — fires on a released left click when
  `menu_on_left_click=False` (typical use: toggle the window).
- Platform notes: **Linux needs libayatana-appindicator**; the tooltip
  is unsupported there and the menu cannot be replaced after creation.

  See [`demo_tray.py`](../../demo_tray.py).
