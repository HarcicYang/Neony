# Roadmap

Neony is a reactive desktop UI framework for Python. This page records
the capabilities that already exist and the work still planned, from an
application developer's point of view.

## Current state

### Reactivity and rendering

- Reactive primitives: `Signal`, `Computed`, `Effect`, `batch()`, and
  cross-window `SharedSignal` writes.
- Declarative bindings: `bind_text()`, `bind_style()`, `bind_attr()`,
  `bind_visible()` on elements and components.
- Coalesced renders: fast typing, hover, and scroll updates do not
  force one synchronous re-render per event.
- Large trees are handled in bounded chunks, and `List` virtualizes
  collections past 200 rows so only the visible window is rendered.
  `DataTable` supports the same bounded-window model through
  `virtualize="auto"` or an explicit boolean.

### Events and input

- Delegated events: mouse, wheel with deltas, scroll position,
  `pointermove` with movement deltas and pointer type, clipboard
  (`paste` / `copy` / `cut`), file drop, and in-app drag lifecycle
  events.
- Rich `DomEvent` payloads: modifier keys, pointer coordinates,
  wheel deltas, scroll position, clipboard text/HTML, drag payloads,
  and dropped files.
- In-app shortcuts: `Page.on_shortcut("Ctrl+S", fn)`, including
  per-platform key dictionaries; window-level `on_keydown` /
  `on_keyup`.

### Lifecycle and window control

- `page.on_close()`, `app.close_handler`, `page.on_focus()` /
  `on_blur()`, navigation / new-window / download policies with per-page
  overrides.
- `show()` / `hide()` / `focus()` / `set_bounds()`, startup and runtime
  window icons, and frameless `TitleBar` chrome.
- Clipboard API: `clipboard_write()` / `clipboard_read()`.

### Components

- Form controls: Button, Input, Textarea, FormField, Checkbox,
  Radio / RadioGroup, Switch, Select, ComboBox, Slider, Progress.
- Overlays: Dialog, Tooltip, Dropdown, Menu / MenuBranch,
  CascadingDropdown, Toast, NoticeBubble.
- Feedback: Alert, Spinner, Skeleton, EmptyState.
- Data views: DataTable, List, Tree.
- Content: Text, Heading, Card, Avatar, Badge, Image.
- Layout: Accordion / Collapsible, ScrollArea, StickToBottom,
  Reorder / ReorderContent.
- Media: managed Video / Audio players with custom transport, local
  `neony://` sources, and HEVC transcode fallback.
- Rich text: `RichText` with text and inline images, caret/selection
  API, IME-safe editing, and image/file paste.
- Chat and notifications: Toast, MessageBubble, NoticeBubble.
- Navigation: Sidebar with sections and panes, Tabs, unified Icon.

### Floating-layer management

- A per-window `LayerManager` owns global floating-layer ordering.
  Components use semantic bands (`TOOLTIP`, `POPOVER`, `MENU`, `MODAL`,
  `TOAST`, `DRAG_GHOST`) instead of component-specific global z-index
  values.
- Numeric z-index and logical stack order are separate. A popup opened
  inside a Dialog can retain its popup z-index while becoming the
  logical topmost layer for outside-click routing.
- Exclusive popup, menu and tooltip groups close through component
  callbacks; modal layers stack in open order and close lower transient
  layers. Owned layers close with their parent.
- `Menu.open_at(..., owner=...)` supports menus mounted at the page root
  but opened from inside another overlay.
- JavaScript scroll indicators, drag ghosts and background layers use
  the same CSS variables generated from the Python layer definitions.
- Known gap: there is no OverlayHost/portal yet. A global overlay can
  still inherit a containing block or clipping boundary from a
  `transform`, `backdrop-filter` or `overflow` ancestor.
- Decision: P3 will add a framework-internal OverlayHost mounted at the
  page root. Overlay components keep their Python API and continue to
  register with `LayerManager`; the host prevents ancestor transforms,
  filters and clipping from changing their containing block. `Layer`
  stays internal and no raw portal/host API is exposed.

### Animation and styling

- Typed CSS models: `Styles`, `Color`, `Border`, `Filter`, `Transform`,
  `BoxShadow`, `Transition`, keyframes, and animation presets.
- Motion tokens and helpers: `motion.stub`, `transition()`,
  `popup_animation()`, `submenu_animation()`.
- Delegated animation events: `transitionend`, `animationstart`,
  `animationend`.

### Theming and i18n

- Eight built-in themed presets across four visual families: Nightglow,
  Planet Plaza, Ember Zone, Cyberangel (dark/light each).
- `DARK`, `LIGHT`, and `DEEP_BLUE` remain aliases; `Theme` is immutable,
  and custom themes register alongside the built-ins.
- Framework i18n with typed catalogs and reactive language switches.

### Platform integration

- Native file dialogs: `open_file()`, `open_files()`, `save_file()`,
  `select_folder()` using the platform picker (zenity/OS native; the
  dialog opens asynchronously).
- File and data URLs: `file_url()`, `data_url()`, and custom
  `neony://` protocol handlers served by Python.
- System tray with native menus and close-to-tray behavior. Linux
  requires `libayatana-appindicator`; tray icon support depends on
  LumiView.
- File drag-and-drop, scroll indicators, smooth horizontal wheel
  scrolling, transparent-window blur on Wayland, and an app name shown
  in the taskbar.

## Component expansion plan

The component work is staged so every release can ship independently.
Each new component is a self-contained change set with implementation,
exports, tests, bilingual API docs, README coverage, Gallery content,
i18n and a runnable demo where appropriate.

### P0: Foundation (implemented)

- [x] Extend `DataTable` virtualization using the fixed-row-height,
  threshold and overscan approach already proven by `List`:
  `DataTable(..., virtualize="auto", row_height=36, overscan=8)`.
- [x] Harden the existing layer contract: focus restoration, topmost
  Escape routing, owner close cascades, nested outside-click behavior
  and regression coverage for combinations of Dialog, Menu, popup and
  Toast.
- [x] Decide the OverlayHost/portal design before implementing new global
  overlay components. Keep `Layer` internal until that design is stable.

### P1: Feedback and forms (implemented)

- [x] `Textarea`
- [x] `FormField`
- [x] `Alert`
- [x] `Spinner`
- [x] `Skeleton`
- [x] `EmptyState`

This batch does not depend on a portal and is the first delivery wave
after the P0 layer checks.

### P2: Navigation and data

- [ ] `SegmentedControl`
- [ ] `Breadcrumb`
- [ ] `Pagination`
- [ ] `Stepper`

These components primarily use ordinary layout, selection and value
bindings; they do not introduce a new global-overlay lifecycle.

### P3: Animated overlays

- [ ] Add the framework-internal OverlayHost/portal for global overlays.
- [ ] `Popover`
- [ ] `Drawer`

`Drawer` is the roadmap's built-in animated container. `Popover` must
use the shared layer manager and declare its owner when opened from an
existing overlay.

### P4: Desktop workflow

- [ ] `CommandPalette`, reusing Dialog lifecycle, Input filtering, the
  List keyboard model and the LayerManager.

### Deferred

These require a separate API and architecture review:

- `AppShell`
- `DatePicker` / `Calendar`
- `SplitView`
- `TagInput`
- advanced DataGrid features such as column pinning, resizing and
  grouping

## Component API examples

### Implemented: P0 and P1

```python
from neony.application import icons
from neony.application.elements import (
    Alert,
    Button,
    Column,
    DataTable,
    EmptyState,
    FormField,
    Input,
    Skeleton,
    Spinner,
    Textarea,
)

table = DataTable(
    columns=[Column("Name", sortable=True), Column("Score", align="right")],
    rows=rows,
    row_key=lambda row: row["name"],
    virtualize="auto",
    row_height=36,
    overscan=8,
)

notes = Textarea("Notes", value="", rows=6, resize="vertical")
notes.bind_value(draft)
notes.on_input(on_preview)
notes.on_change(on_save)

email = FormField("Email", Input(type="email"), help="Never shared.", required=True)
email.invalid = True
email.error = "Invalid email"

undo = Button("Undo")
alert = Alert(
    "Saved",
    description="All changes synced.",
    variant="success",
    dismissible=True,
    actions=[undo],
)


def undo_changes(_event):
    revert_changes()
    alert.dismiss()


undo.on_click(undo_changes)
alert.on_dismiss(lambda _alert: update_status())

loading = Spinner("Loading projects", size="20px", role="accent")
loading.label = "Saving..."

skeleton = Skeleton(variant="text", lines=3, width="70%")
skeleton.animation = False

empty = EmptyState(
    "No projects",
    description="Create one to start.",
    icon=icons.star,
    actions=[Button("New project")],
)
```

### Planned: P2-P4

These examples describe planned public shapes. They follow the existing
`Component`, `bind_value` / `bind_selected`, theme-token and
popup-lifecycle conventions.

```python
from neony.application import icons
from neony.application.elements import (
    Breadcrumb,
    BreadcrumbItem,
    Button,
    Command,
    CommandPalette,
    Drawer,
    Pagination,
    Popover,
    Segment,
    SegmentedControl,
    Step,
    Stepper,
)

view = SegmentedControl(Segment("list", "List"), Segment("grid", "Grid"), value="list")
view.value = "grid"
view.bind_value(view_mode)
view.on_change(on_view_change)

crumbs = Breadcrumb(
    BreadcrumbItem("Workspace", key="workspace"),
    BreadcrumbItem("Neony", key="neony"),
    BreadcrumbItem("Settings", key="settings", disabled=True),
)
crumbs.on_change(lambda event: router.go(event.value))

pager = Pagination(value=1, page_count=20, siblings=1)
pager.value = 4
pager.page_count = 24
pager.bind_value(page_signal)
pager.on_change(on_page_change)

steps = Stepper(
    Step("Account", account_form, key="account"),
    Step("Plan", plan_form, key="plan"),
    Step("Review", review_panel, key="review"),
    active_key="account",
)
steps.selected_key = "plan"
steps.bind_selected(step_signal)
steps.on_change(on_step_change)

popover = Popover(
    anchor=Button("Filters"),
    content=filter_panel,
    placement="bottom",
    align="start",
)
popover.open = True
popover.toggle()
popover.on_open(on_opened)
popover.on_close(on_closed)

drawer = Drawer(
    notification_panel,
    title="Notifications",
    side="right",
    width="360px",
    closable=True,
)
drawer.open = True
drawer.on_open(on_opened)
drawer.on_close(on_closed)

palette = CommandPalette(
    Command("open", "Open file", keywords=("file",), shortcut="Ctrl+O", icon=icons.star),
    hotkey={"default": "Ctrl+K", "darwin": "Meta+K"},
)
palette.open = True
palette.query = "open"
palette.add_command(Command("theme", "Change theme"))
palette.on_change(run_command)
```

Planned item models:

- `Segment(value, label, icon=None, disabled=False)`
- `BreadcrumbItem(label, key=None, icon=None, disabled=False)`
- `Step(title, content, key=None, description=None, icon=None)`
- `Command(value, label, description="", keywords=(), shortcut=None, icon=None, disabled=False)`

## Delivery contract

- Every component uses composed `Component` trees, internal state,
  source-aware user events and theme tokens. Raw HTML, JavaScript and
  CSS remain outside the public API.
- Global overlays register with `LayerManager`. Components must not
  embed new global z-index constants, and an overlay opened from
  another overlay must declare its owner.
- Compound controls containing popup buttons must not use a `<label>`
  root that can implicitly activate the first option. Connect visible
  labels with `aria-labelledby` or an equivalent explicit relationship.
- New Python components normally do not need JavaScript changes; any
  change under `src/neony/javascript/` requires Vitest coverage.
- No new runtime dependency is added without a separate design review.
- Acceptance is `uv run python scripts/check_all.py`; display-dependent
  work also runs the smoke suite under `xvfb-run`.

## Platform priorities

- **macOS (WKWebView) verification** — the platform is not yet a
  verified target; HiDPI / mixed-DPI scaling also needs verification.
- **Native installers and packaging** — evaluate a packaging path
  (for example Briefcase) if MSI / AppImage / .app installers are
  wanted.

## Non-goals for now

- X11 is not a supported Linux target: test on Wayland.
- Raw HTML/JS/CSS are not part of the public API; the framework exposes
  typed Python objects only.
