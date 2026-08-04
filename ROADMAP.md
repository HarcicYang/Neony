# Roadmap

Planned work, roughly in priority order.

## Performance

- [x] **Hover de-noise** — `mouseover`/`mouseout`/`focus`/`blur` render deferred (one frame of coalescing)
- [ ] **Input throttling** — coalescing render pipeline in place; `on_input` still renders per keystroke, hooking it into the deferred path is a one-line change
- [x] **Dirty-subtree diffing** — only changed elements re-serialize; mutations mark their ancestors dirty
- [x] **Snapshot reuse** — unchanged subtrees reuse cached snapshots, skipping `to_node()`
- [x] **Style direct-patch** — pure style changes bypass the full diff

## Reactivity

- [x] **Signal primitives** — `Signal` / `Computed` / `Effect` with automatic dependency tracking and `batch()` coalescing
- [x] **Declarative bindings** — `bind_text()` / `bind_style()` / `bind_attr()` / `bind_visible()` on elements and components
- [x] **Cross-window reactivity** — a shared signal write updates every window with a binding
- [x] **JS unit tests** — vitest + jsdom cover the browser runtime (event delegation, patch engine)

## Events

- [ ] **Scroll & wheel events** — `wheel` and `scroll` in the delegation table, with delta values in the event payload
- [ ] **Pointer move events** — `pointermove` / `mousemove` for sliders, drawing, tooltip-follow, drag feedback
- [ ] **Drag-and-drop events** — `dragstart` / `dragover` / `drop` for file drop and in-app drag reorder
- [ ] **Clipboard events** — `paste` / `copy` / `cut` for rich-text fields and paste-from-clipboard workflows
- [ ] **Rich event payload** — `DomEvent` currently carries only `key` / `type` / `value`. Add modifier keys (`ctrl` / `shift` / `meta` / `alt`), mouse coordinates (`x` / `y`), and wheel delta (`delta_x` / `delta_y`) so shortcut keys, right-click menus, and scroll-aware UIs work without `eval_js`.

## Lifecycle

- [x] **Page close hook** — `page.on_close(fn)`, wired to the native `CloseRequested` event internally
- [x] **App shutdown hook** — `app.close_handler`, runs after all windows close
- [x] **Element reuse defense** — mounting the same element twice raises a clear `RuntimeError`
- [ ] **Window focus/blur events** — detect which window is active in multi-window apps (depends on lumiview upstream)
- [ ] **Window navigation control** — expose `set_on_navigation` / `set_on_new_window` / download events from lumiview's Window API

## Components

- [ ] **Form controls** — Radio, Switch, Select/ComboBox, Slider, Progress
- [ ] **Overlays** — Dialog/Modal, Tooltip, Dropdown, Menu (depend on pointer-move events and rich event payload for positioning)
- [ ] **Data views** — DataTable, List, Tree
- [ ] **Content** — Card, Avatar, Badge, Image

## Animation

- [ ] **CSS `transition` support** in `Styles`
- [ ] **Built-in animated containers**
- [ ] **Transition hooks**

## Platform integration

- [ ] **File dialogs** — open/save file via native OS dialog
- [ ] **Window icon** — `Window.set_icon()` via `Config.window.icon`
- [ ] **Window state query** — `get_size()` / `get_bounds()` / `show()` / `hide()` / `focus()` / `set_bounds()` exposed on `NeonApplication`
- [ ] **Clipboard API** — typed wrapper around `navigator.clipboard` (read/write text, images)
- [ ] **Local resource URL helper** — `file://` / data-URL encoding for Windows paths, spaces, non-ASCII filenames
- [ ] **System tray** — tray icon with context menu (tao-supported, needs lumiview upstream)
- [ ] **Global shortcuts** — app-wide keybindings that work even when the window is not focused (tao-supported, needs lumiview upstream)

## Platform verification

- [x] **Windows (WebView2)**
- [ ] **macOS (WKWebView)**
- [x] **Linux desktops (Wayland)**
- [ ] **HiDPI / mixed-DPI scaling**

> NOTE:
> For Linux, we won't test on x11, please do it yourself
> For macOS, we don't have a device to test on, please do it yourself too.
