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
- Overlays: Dialog, PromptDialog, Popover, Drawer, CommandPalette,
  Tooltip, Dropdown, Menu / MenuBranch, CascadingDropdown, Toast,
  NoticeBubble.
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
- Each Page owns an internal `OverlayHost` placed after the content
  column. Portal-marked global overlay roots move into that host during
  `Page.build()`, so transformed, filtered or overflow-clipped content
  ancestors cannot become their containing block.
- Dialog, PromptDialog, Popover's panel, Drawer, CommandPalette, Menu
  and Toast use the portal path automatically. Overlay components keep
  their Python API and continue to register with `LayerManager`; no raw
  portal or host API is exposed.

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

## Component capability expansion plan v2

This plan records the next component work from an application
developer's point of view. It separates capabilities already delivered
from the remaining gaps, and replaces the older P2-P4/Deferred queue.
Each phase can ship independently and includes implementation, exports,
Python and JavaScript tests where applicable, bilingual API docs, README
coverage, Gallery content, i18n and a runnable demo where appropriate.

### Delivered baseline

- DataTable and List bounded-window virtualization.
- Floating-layer ordering, owner cascades, nested outside-click routing,
  focus capture/restore and regression coverage across Dialog, Menu,
  popup and Toast combinations.
- `Textarea`, `FormField`, `Alert`, `Spinner`, `Skeleton`, `EmptyState`.

### Capability status matrix

| Area | Implemented for v2 | Remaining |
| --- | --- | --- |
| Menu and choices | shared rich `ChoiceItem` model across Menu, Dropdown, Select, ComboBox and CascadingDropdown | further menu composition only when needed |
| Form interaction | Input v2, validation contract, loading Button and indeterminate Checkbox | Form-level orchestration |
| Collection data | sorting, single / multi selection and bounded virtualization | filtering, search, visibility, expandable rows, editing and pagination integration |
| Tree navigation | static hierarchy, expansion and leaf selection | tri-state checkboxes, lazy loading, search, node actions and virtualization |
| List navigation | single-select virtualization | groups, multi-select, subtitles, trailing actions and loading / empty slots |
| Overlays | OverlayHost, focus contracts, Dialog, Popover, Drawer, CommandPalette, Menu and Toast | none required for v2 |
| Workflow input | select, combobox, slider and progress | MultiSelect, TagInput, file upload, NumberInput and OTP |
| Layout tools | Flex, GridView, ScrollArea and SplitView review | resizable split panes |
| Advanced content | Markdown, RichText and media | ColorPicker, Rating, Timeline and Descriptions |

### P0: Shared contracts (implemented)

- [x] Add `ChoiceItem` and `MenuSeparator`; preserve all string, tuple and
  `MenuBranch` call sites while moving Menu, Dropdown, Select, ComboBox
  and CascadingDropdown onto one normalized choice model.
- [x] Add `focus_scope="trap"` and `initial_focus` to the internal layer
  contract, integrate them with Dialog and cover Tab/Shift+Tab routing.
- [x] Add the FormField validation contract (`validator` and
  `validate()`), leaving Form-level orchestration to a later phase.
- No user-facing component is added in P0. This phase unlocks later
  overlays and input components without duplicating their foundations.

### P1: Everyday UI quick wins (implemented)

- [x] Input v2: prefix/suffix, clear action, password reveal and Enter
  submit.
- [x] Button loading/busy state and Checkbox indeterminate state.
- [x] `SegmentedControl`, `Breadcrumb`, `Pagination` and navigation
  `Stepper`.
- These components use ordinary layout, selection and value bindings;
  they do not require the portal.

### P2: Overlay and productivity (implemented)

- [x] Add the Page-owned OverlayHost/portal for global overlays and move
  Dialog, PromptDialog, Menu, Toast, Drawer, CommandPalette and the
  Popover panel into it automatically.
- [x] Add `Popover` with viewport-aware placement, flip / clamp behavior,
  scroll and resize repositioning, owner-aware nesting and optional
  focus trapping.
- [x] Add `Drawer` with four sides, configurable thickness, scrim
  close control, directional animation and the shared modal focus trap.
- [x] Add `CommandPalette` and `Command`, with local filtering, disabled
  rows, keyboard selection, duplicate guards, selection events and
  Page-collected hotkeys.

### P3: Data and collection depth

- DataTable filtering/search, column visibility, expandable rows,
  inline editing and external Pagination integration.
- Tree tri-state selection, lazy loading, search, node actions and
  virtualization.
- List groups, multi-select, subtitles, trailing actions, loading and
  empty-state slots.

### P4: Form and input depth

- Form-level validation, submit orchestration and cross-field rules.
- `MultiSelect`, `TagInput`, `FileUpload`/`DropZone`, `NumberInput` and
  `OTP`.
- These build on the P0 choice and validation contracts plus the P2
  OverlayHost.

### P5: Advanced desktop controls

- `DatePicker`, `Calendar`, `DateRange` and `TimePicker`.
- `SplitView`, `ColorPicker`, `Rating`, `Timeline` and `Descriptions`.
- `AppShell` remains a separate architecture review.

### Delivery contract

- Every phase lands as an independently verifiable change set with
  Python tests, bilingual docs and Gallery coverage.
- Any change under `src/neony/javascript/*` requires Vitest coverage.
- Display-dependent acceptance runs under `xvfb-run`.
- No new runtime dependency is added without a separate design review.

## Component API examples

### Delivered baseline

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

email = FormField(
    "Email",
    Input(type="email"),
    help="Never shared.",
    required=True,
    validator=lambda value: None if "@" in value else "Invalid email",
)
email.validate()

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

### Implemented: P0 shared contracts

```python
from neony.application import icons
from neony.application.elements import (
    ChoiceItem,
    Dialog,
    DialogAction,
    FormField,
    Input,
    Menu,
    MenuSeparator,
    Select,
)

menu = Menu(
    ChoiceItem("rename", "Rename", icon=icons.edit, shortcut="F2"),
    MenuSeparator(),
    ChoiceItem("delete", "Delete", danger=True),
)

plan = Select(
    "Plan",
    options=[
        ChoiceItem("free", "Free"),
        ChoiceItem("pro", "Pro"),
        ChoiceItem("legacy", "Legacy", disabled=True),
    ],
)

confirm = Input(placeholder="Type CONFIRM")
dialog = Dialog(
    title="Delete project",
    content=confirm,
    initial_focus=confirm,
    actions=[DialogAction("Delete", variant="danger")],
)

email = FormField(
    "Email",
    Input(type="email"),
    required=True,
    validator=lambda value: None if "@" in value else "Invalid email",
)
email.validate()
```

### Implemented: P1 daily controls

```python
save = Button("Save", loading=busy)
select_all = Checkbox("Select all", indeterminate=True)

email = Input(
    prefix=icons.email,
    suffix=".com",
    clearable=True,
)
email.on_submit(send)
password = Input(type="password", reveal_password=True)

view = SegmentedControl(
    ChoiceItem("list", "List", icon=icons.list),
    ChoiceItem("grid", "Grid", icon=icons.grid_view),
)
view.bind_value(view_mode)

crumbs = Breadcrumb("Workspace", ("project", "Neony"), "Settings")
pager = Pagination(value=1, page_count=20)
pager.bind_value(page)

steps = Stepper(
    Step("Account", account_form, key="account"),
    Step("Plan", plan_form, key="plan"),
    linear=True,
)
steps.bind_selected(step_key)
```

### Implemented: P2 overlay productivity

```python
filters = Popover(Button("Filters"), filter_panel, placement="bottom")
filters.open = True

drawer = Drawer(notification_panel, side="right", title="Notifications")
drawer.open = True

palette = CommandPalette(
    Command("open", "Open file", keywords=("document",), shortcut="Ctrl+O"),
    Command("theme", "Change theme"),
    hotkey={"darwin": "Meta+Shift+P", "default": "Ctrl+Shift+P"},
)
palette.on_change(run_command)
```

### Remaining: P3-P5

The phase lists above are the source of truth for work not yet
implemented. The P0-P2 public shapes are documented in the component API
reference and the Gallery; future APIs remain non-binding until their
phase lands.

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
