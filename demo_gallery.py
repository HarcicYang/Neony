#!/usr/bin/env python3
"""Neony component gallery — every component with docs and code samples.

Each tab pairs a live component demo with a short description and the
Python snippet that produced it, so the gallery doubles as a reference.

Showcases: Button variants, Input types, Checkbox state, layout
primitives (HStack/Flex/Spacer), typography roles, frosted glass,
window icon, rich event payloads (modifiers / coordinates / wheel),
file drag-and-drop, clipboard events + API, in-app shortcuts, reactive
primitives (Signal / Computed / Effect / bindings), the Sidebar
component, and window-state control (show / hide / focus / set_bounds).

Usage:
    python demo_gallery.py
"""

import asyncio
import os
import sys

from neony.application import Config, NeonApplication, Page, WebViewConfig, WindowConfig
from neony.application.elements import (
    Button,
    Checkbox,
    Component,
    Flex,
    GlassPanel,
    Heading,
    HStack,
    Input,
    Separator,
    Sidebar,
    SidebarItem,
    Spacer,
    Tabs,
    Text,
    TitleBar,
    VStack,
)
from neony.dom import Color, Computed, Div, DOMElement, DomEvent, Signal, Styles, effect

# Frameless + transparent: the gallery gets its own glass TitleBar, and
# the desktop shows through the frosted chrome.
app = NeonApplication(
    Config(
        window=WindowConfig(
            title="Neony — Component Gallery",
            width=560,
            height=720,
            decorations=False,
            transparent=True,
        ),
        webview=WebViewConfig(devtools=True),
    )
)

_BACKGROUND_URL = "https://harcic.is-a.dev/resource/backgrounds/8.webp"
_ICON_URL = "https://harcic.is-a.dev/resource/favicon.svg"

_MONO = "ui-monospace, 'SF Mono', Menlo, Consolas, monospace"


def CodeBlock(code: str) -> DOMElement:
    """Render *code* as a monospace, surface-toned block."""
    return Div(
        styles=Styles(
            background_color=Color(var="--color-surface"),
            border_radius="8px",
            padding="12px 16px",
            border="1px solid var(--color-border)",
            font_family=_MONO,
            font_size="12px",
            line_height="1.6",
            white_space="pre",
            overflow="auto",
            color=Color(var="--color-text-secondary"),
        ),
        container=[code],
    )


def Section(title: str, blurb: str, code: str, *demos: Component | DOMElement) -> VStack:
    """One gallery section: heading, description, code sample, live demo."""
    return VStack(
        Heading(title, level=3),
        Text(blurb, role="secondary"),
        CodeBlock(code),
        Separator(),
        *demos,
        gap="12px",
        align="stretch",
    )


def StatusChip(label: str) -> tuple[HStack, Div]:
    """A small label + status-dot pair, updated by event handlers.
    Returns ``(chip, dot)`` so handlers can light the dot up."""
    dot = Div(
        styles=Styles(
            width="10px",
            height="10px",
            border_radius="50%",
            background_color=Color(var="--color-border"),
            flex_shrink="0",
        )
    )
    chip = HStack(
        dot,
        Text(label, size="12px", role="secondary"),
        gap="6px",
        align="center",
    )
    return chip, dot


def set_dot(dot: Div, active: bool) -> None:
    """Light (or dim) a status dot."""
    dot.styles.background_color = Color(var="--color-accent") if active else Color(var="--color-border")


def Mono(size: str = "13px") -> Div:
    """A monospace, muted single-line readout; update via ``container``."""
    return Div(
        styles=Styles(
            font_family=_MONO,
            font_size=size,
            color=Color(var="--color-text-secondary"),
        )
    )


# ── header (shared across tabs) ──────────────────────────────────

_MODE_LABELS = {"dark": "Light mode", "light": "Deep Blue mode", "deep-blue": "Dark mode"}

theme_btn = Button("Light mode", variant="ghost")


async def on_theme_click(event: DomEvent) -> None:
    app.theme.toggle()
    await app.sync_theme()
    theme_btn.label = _MODE_LABELS[app.theme.mode]


theme_btn.on_click(on_theme_click)

header = VStack(
    Heading("Neony Component Gallery", level=1),
    Text("Every component, one page — with docs and code samples", role="secondary"),
    HStack(Spacer(), theme_btn, gap="8px"),
    Separator(),
    gap="12px",
)

# ── tab: buttons ─────────────────────────────────────────────────

primary_btn = Button("Primary Action")
ghost_btn = Button("Ghost Button", variant="ghost")
danger_btn = Button("Delete", variant="danger")
disabled_btn = Button("Disabled", disabled=True)

# reset_styles demo: custom green button, hover feedback still works
custom_btn = Button("Custom").reset_styles(
    Styles(
        padding="10px 20px",
        border_radius="20px",
        border="none",
        background_color=Color(hex="#2fa89a"),
        color=Color(name="white"),
        font_weight="600",
        cursor="pointer",
        transition="all 0.15s ease",
    )
)

buttons_panel = Section(
    "Buttons",
    "Three variants (primary, ghost, danger) with hover / press feedback "
    "and colour-matched glows — hover lifts with a halo in the variant's "
    "own colour, focus draws a tinted ring. reset_styles() replaces the "
    "base look while keeping the feedback.",
    """Button("Primary Action")
Button("Ghost Button", variant="ghost")
Button("Delete", variant="danger")
Button("Disabled", disabled=True)
Button("Custom").reset_styles(
    Styles(background_color=Color(hex="#2fa89a"), ...))""",
    primary_btn,
    ghost_btn,
    danger_btn,
    disabled_btn,
    custom_btn,
)

# ── tab: inputs ──────────────────────────────────────────────────

text_input = Input(placeholder="Your name…")
text_echo = Text("", role="secondary")

password_input = Input(placeholder="Password", type="password")
password_echo = Text("", role="secondary")

email_input = Input(placeholder="Email", type="email")
email_echo = Text("", role="secondary")


async def on_text_input(event: DomEvent) -> None:
    text_echo.text = f"Hello, {event.value}!" if event.value else ""


async def on_password_input(event: DomEvent) -> None:
    password_echo.text = f"Length: {len(event.value)}" if event.value else ""


async def on_email_input(event: DomEvent) -> None:
    email_echo.text = f"Email: {event.value}" if event.value else ""


text_input.on_input(on_text_input)
password_input.on_input(on_password_input)
email_input.on_input(on_email_input)

inputs_panel = Section(
    "Inputs",
    "Text, password and email fields. The on_input event carries the live "
    "value; echoing it back is the standard pattern.",
    """inp = Input(placeholder="Your name…")
async def on_text_input(event: DomEvent) -> None:
    text_echo.text = f"Hello, {event.value}!"
inp.on_input(on_text_input)""",
    text_input,
    text_echo,
    password_input,
    password_echo,
    email_input,
    email_echo,
)

# ── tab: checks ──────────────────────────────────────────────────

FOODS = ["Pizza", "Tacos", "Ramen"]
food_checks = [Checkbox(name) for name in FOODS]
check_all = Checkbox("Select all")
check_status = Text("0 of 3 selected", role="secondary")


def refresh_checks() -> None:
    n = sum(1 for cb in food_checks if cb.checked)
    check_all.checked = n == len(FOODS)
    check_status.text = f"{n} of {len(FOODS)} selected"


for cb in food_checks:
    cb.on_change(lambda _e: refresh_checks())


async def on_check_all(event: DomEvent) -> None:
    for cb in food_checks:
        cb.checked = bool(event.value)
    refresh_checks()


check_all.on_change(on_check_all)

checks_panel = Section(
    "Checkboxes",
    "Custom-styled toggles with a change event. Setting .checked "
    "programmatically updates the view but never fires callbacks.",
    """cb = Checkbox("Pizza")
cb.checked = True  # programmatic — no callback fires
cb.on_change(lambda e: print(e.value))""",
    check_all,
    *food_checks,
    check_status,
)

# ── tab: layout ──────────────────────────────────────────────────

# HStack: row layout with a Spacer pushing the button to the right
row_example = HStack(
    Text("Title", weight="600"),
    Spacer(),
    Button("Edit", variant="ghost"),
    gap="8px",
)

# Flex: full control (wrap demo)
wrap_example = Flex(
    *[Button(f"Item {i}", variant="ghost") for i in range(6)],
    direction="row",
    wrap="wrap",
    gap="8px",
)

layout_panel = Section(
    "Layout",
    "HStack rows with Spacer pushing content; Flex gives full control, including wrapping.",
    """HStack(Text("Title"), Spacer(), Button("Edit"), gap="8px")
Flex(*items, direction="row", wrap="wrap", gap="8px")""",
    row_example,
    wrap_example,
)

# ── tab: typography ──────────────────────────────────────────────

# user_select demo: text that cannot be selected, next to normal text.
noselect = Div(
    styles=Styles(user_select="none", opacity="0.7"),
    container=[Text("Locked copy — user_select='none' blocks selection.", role="secondary").build()],
)

typography_panel = Section(
    "Typography",
    "Six heading levels plus semantic text roles that follow the theme. "
    "user_select controls text selection: the first row below cannot be "
    "highlighted, the second can.",
    """Heading("Title", level=1)
Text("Body copy")
Text("Muted copy", role="secondary")
Text("Danger", role="danger")
Div(styles=Styles(user_select="none"), ...)""",
    Heading("Heading 1", level=1),
    Heading("Heading 2", level=2),
    Heading("Heading 3", level=3),
    Heading("Heading 4", level=4),
    Heading("Heading 5", level=5),
    Heading("Heading 6", level=6),
    Text("Primary text — the default body copy."),
    Text("Secondary text — muted, less important.", role="secondary"),
    Text("Danger text — errors and destructive emphasis.", role="danger"),
    Text("Success text — confirmations.", role="success"),
    noselect,
    Text("Selectable copy — the normal default."),
)

# ── tab: glass ───────────────────────────────────────────────────

glass_input = Input(placeholder="Glass input…", glass=True)
glass_input_echo = Text("", role="secondary")


async def on_glass_input(event: DomEvent) -> None:
    glass_input_echo.text = f"Typed: {event.value}" if event.value else ""


glass_input.on_input(on_glass_input)

# One frosted stage carries the background image; the glass components
# inside it (glass=True, no background of their own) blur it through
# their translucent, theme-tinted surfaces.  role="accent" adds a
# persistent colour-matched glow around the panel.
glass_demo = GlassPanel(
    Heading("Frosted Stage", level=4),
    Text(
        "Components inside keep their theme colours while gaining the frosted look.",
        role="secondary",
    ),
    HStack(
        Button("Primary", glass=True),
        Button("Ghost", variant="ghost", glass=True),
        Button("Danger", variant="danger", glass=True),
        gap="8px",
    ),
    glass_input,
    glass_input_echo,
    Checkbox("Glass checkbox", glass=True),
    gap="16px",
    background=_BACKGROUND_URL,
    role="accent",
)

# Role glows: a semantic role tints both the hairline border and the
# persistent outer glow — success below, danger right.
success_stage = GlassPanel(
    Text("Success — role glows follow the theme", role="success"),
    gap="8px",
    padding="12px 16px",
    role="success",
)
danger_stage = GlassPanel(
    Text("Danger — destructive emphasis", role="danger"),
    gap="8px",
    padding="12px 16px",
    role="danger",
)

# Per-corner radii: each corner gets its own rounding — useful when a
# panel joins rounded chrome (e.g. the titlebar / sidebar seams).
corners_stage = GlassPanel(
    Text("Per-corner radii — 24px / 4px / 24px / 4px", role="secondary"),
    gap="8px",
    padding="12px 16px",
    border_top_left_radius="24px",
    border_top_right_radius="4px",
    border_bottom_left_radius="24px",
    border_bottom_right_radius="4px",
)

glass_panel = Section(
    "Frosted Glass",
    "GlassPanel blurs the background image; components with glass=True "
    "keep their theme colours while gaining the frosted surface. A "
    "semantic role tints the panel's border AND its outer glow; "
    "per-corner radii join chrome at any angle.",
    """GlassPanel(Heading("Frosted"), background=url, role="accent")
GlassPanel(Text("…"), role="success")
GlassPanel(..., border_top_left_radius="24px", ...)
Button("Primary", glass=True)
Checkbox("Glass", glass=True)""",
    glass_demo,
    success_stage,
    danger_stage,
    corners_stage,
)

# ── tab: icon ─────────────────────────────────────────────────────

# Frameless windows have no OS window chrome, so the icon can't be set
# via WindowConfig — it's painted inline in the TitleBar instead.  The
# window header above shows the live result.
icon_panel = Section(
    "Window Icon",
    "Frameless windows show the icon inline in the TitleBar; decorated "
    "windows hand it to the OS window chrome via WindowConfig.icon — "
    "both take the same URL or file path. file_url() / data_url() turn "
    "local files into URL strings for icons, backgrounds and images.",
    """# Frameless — inline in the TitleBar (this window):
TitleBar("My App", icon="https://harcic.is-a.dev/resource/favicon.svg")

# Decorated — the OS window chrome shows it:
launch(page, title="My App", icon="icon.png")
# or: Config(window=WindowConfig(title="My App", icon="icon.png"))

# Runtime swap (either mode):
await app.set_icon("icon.png")

# Local resources:
from neony.application import file_url, data_url
GlassPanel(background=file_url("bg.png"))
TitleBar(icon=data_url("logo.svg"))""",
    VStack(
        Text("Live: the favicon in the titlebar above uses TitleBar(icon=...).", role="secondary"),
        Text(
            "For decorated windows the taskbar / titlebar icon comes from "
            "WindowConfig.icon; TitleBar(icon=...) only affects frameless chrome.",
            role="secondary",
        ),
        gap="8px",
        align="stretch",
    ),
)

# ── tab: events ──────────────────────────────────────────────────

# Mouse tracker: mousedown anywhere inside the zone (even on its text
# labels) bubbles to this _bubble_events Div.  The DomEvent carries the
# viewport (x/y) and element-relative (offset_x/offset_y) coordinates.
tracker_text = Text("Click anywhere in this box", role="secondary")
click_pos = Mono()
click_pos.container = ["—"]

tracker = Div(
    styles=Styles(
        border="1px solid var(--color-border)",
        border_radius="8px",
        padding="16px",
        min_height="90px",
        display="flex",
        flex_direction="column",
        gap="8px",
        justify_content="center",
    ),
    container=[tracker_text.build(), click_pos],
)
tracker._bubble_events = True


async def on_tracker_down(event: DomEvent) -> None:
    click_pos.container = [
        f"down at ({event.x:.0f}, {event.y:.0f})  offset ({event.offset_x:.0f}, {event.offset_y:.0f})"
    ]


tracker.on_mousedown(on_tracker_down)

# Modifier keys: window-level handlers (registered on the Page below)
# — the lights follow Ctrl / Shift / Alt / Meta wherever keys land,
# no input focus required.
mod_input = Input(placeholder="Type anywhere — the lights follow the modifiers…")
ctrl_chip, ctrl_dot = StatusChip("Ctrl")
shift_chip, shift_dot = StatusChip("Shift")
alt_chip, alt_dot = StatusChip("Alt")
meta_chip, meta_dot = StatusChip("Meta")


async def on_mod_key(event: DomEvent) -> None:
    # Both keydown and keyup carry the pressed set at that moment, so
    # re-syncing the lights from the event is enough — no state to keep.
    set_dot(ctrl_dot, event.ctrl_key)
    set_dot(shift_dot, event.shift_key)
    set_dot(alt_dot, event.alt_key)
    set_dot(meta_dot, event.meta_key)


# Wheel deltas: scroll inside the zone; the handler reads delta_x/delta_y.
# WebKitGTK delivers one event per notch in PIXEL mode (delta_mode=0)
# with a constant fractional delta (±94.5 per notch, verified on 2.52);
# trackpads give continuous fractional deltas in the same mode. Line
# mode (delta_mode=1, x16) occurs on other backends. The readout
# converts to pixels via the mode factor and keeps a running total.
# The readout sits BELOW the scrollable zone so it stays visible while
# the content scrolls away.
wheel_total_y = {"px": 0.0}
wheel_delta = Mono()
wheel_delta.container = ["dx: —   dy: —   total: 0px"]
wheel_zone = Div(
    styles=Styles(
        border="1px solid var(--color-border)",
        border_radius="8px",
        padding="16px",
        height="120px",
        overflow="auto",
    ),
    container=[
        Div(
            styles=Styles(height="300px", padding_top="4px"),
            container=[
                Text("Tall content so the zone scrolls…", role="secondary").build(),
                Text("Keep scrolling to see live deltas.", role="secondary").build(),
            ],
        )
    ],
)
wheel_zone._bubble_events = True


async def on_wheel(event: DomEvent) -> None:
    # delta_mode: 0 = pixels, 1 = lines (x16), 2 = pages (x256).
    factor = 16 ** (event.delta_mode or 0)
    px = (event.delta_y or 0) * factor
    wheel_total_y["px"] += px
    wheel_delta.container = [
        f"dy: {event.delta_y:+.0f} (mode {event.delta_mode})   "
        f"dx: {event.delta_x:+.0f}   total: {wheel_total_y['px']:+.0f}px"
    ]


wheel_zone.on_wheel(on_wheel)

events_panel = Section(
    "Rich Events",
    "Every delegated event carries the full payload: modifier keys "
    "(ctrl/shift/alt/meta), viewport and element-relative mouse "
    "coordinates, and wheel deltas. Click the box, hold modifiers while "
    "typing, scroll the zone.",
    """div.on_mousedown(lambda e: f"{e.x}, {e.y} — {e.offset_x}, {e.offset_y}")
div.on_keydown(lambda e: e.ctrl_key or e.meta_key)
div.on_wheel(lambda e: f"dx: {e.delta_x}  dy: {e.delta_y}")""",
    tracker,
    HStack(mod_input, gap="8px"),
    HStack(ctrl_chip, shift_chip, alt_chip, meta_chip, gap="16px"),
    Text(
        "Meta (Super) is often reserved by the window manager on Linux — "
        "hyprland grabs it for its own bindings, so it may never reach "
        "the page. The other three modifiers always arrive.",
        role="secondary",
        size="12px",
    ),
    wheel_zone,
    wheel_delta,
)

# ── tab: drop ────────────────────────────────────────────────────

drop_hint = Text("Drop files anywhere in this box", role="secondary")
drop_list = Div(
    styles=Styles(font_family=_MONO, font_size="12px", line_height="1.7", white_space="pre"),
    container=[""],
)

drop_zone = Div(
    styles=Styles(
        border="2px dashed var(--color-border)",
        border_radius="8px",
        padding="20px",
        min_height="140px",
        display="flex",
        flex_direction="column",
        gap="8px",
        justify_content="center",
        align_items="center",
        transition="all 0.15s ease",
    ),
    container=[drop_hint.build(), drop_list],
)
drop_zone._bubble_events = True


def fmt_size(size: int) -> str:
    """Human-readable byte count."""
    if size >= 1024 * 1024:
        return f"{size / 1024 / 1024:.1f} MB"
    if size >= 1024:
        return f"{size / 1024:.1f} KB"
    return f"{size} B"


async def on_drop_over(event: DomEvent) -> None:
    drop_zone.styles = drop_zone.styles.model_copy(
        update={
            "border": "2px dashed var(--color-accent)",
            "background_color": Color(var="--color-surface"),
        }
    )
    drop_hint.text = "Release to drop"


async def on_drop_leave(event: DomEvent) -> None:
    drop_zone.styles = drop_zone.styles.model_copy(
        update={"border": "2px dashed var(--color-border)", "background_color": None}
    )
    drop_hint.text = "Drop files anywhere in this box"


async def on_drop(event: DomEvent) -> None:
    drop_zone.styles = drop_zone.styles.model_copy(
        update={"border": "2px dashed var(--color-border)", "background_color": None}
    )
    drop_hint.text = "Drop files anywhere in this box"
    if not event.drop_files:
        drop_list.container = ["(no files — on WKWebView the file path is empty)"]
        return
    lines = [f"{f['name']}   ({fmt_size(f['size'])}, {f['type']})" for f in event.drop_files]
    lines.append("")
    lines.extend(f"path: {f['path'] or '<unavailable>'}" for f in event.drop_files)
    drop_list.container = ["\n".join(lines)]


drop_zone.on_dragover(on_drop_over)
drop_zone.on_dragleave(on_drop_leave)
drop_zone.on_drop(on_drop)

drop_panel = Section(
    "File Drop",
    "Drag files from the file manager into the dashed zone. The drop "
    "event carries each file's name, local filesystem path, size and "
    "MIME type. On WebKitGTK the webview reports empty files, so Neony "
    "takes the drop over at the native layer, hit-tests the position, "
    "and re-dispatches the drop event with the real paths; on WebView2 "
    "File.path arrives directly, on WKWebView it is empty. "
    "dragover/dragleave/drop are all delegated, and the browser's "
    "navigate-on-drop default is prevented for you.",
    """zone = Div(styles=Styles(border="2px dashed var(--color-border)"))
zone.on_dragover(lambda e: highlight(zone))
zone.on_dragleave(lambda e: unhighlight(zone))
zone.on_drop(lambda e: [print(f["name"], f["path"]) for f in e.drop_files])""",
    drop_zone,
)

# ── tab: clipboard ───────────────────────────────────────────────

clip_log = Text("", role="secondary")
paste_input = Input(placeholder="Paste (Ctrl+V) into this field…")
clip_line = Mono(size="12px")


def clip_log_line(line: str) -> None:
    """Keep the last 4 log lines."""
    lines = [ln for ln in (clip_log.text or "").splitlines() if ln][-3:]
    lines.append(line)
    clip_log.text = "\n".join(lines)


async def on_paste(event: DomEvent) -> None:
    # clipboard_text may be None on some backends — the input's own
    # value (updated by the input event right after) is the fallback.
    if event.clipboard_text is None:
        clip_line.container = ["clipboard_text: <not exposed by this backend>"]
    else:
        clip_line.container = [
            (
                f"clipboard_text: {event.clipboard_text!r}"
                + (f"  html: {event.clipboard_html!r}" if event.clipboard_html else "")
            )
        ]
    clip_log_line("paste event — clipboard carried into Python")


async def on_paste_input(event: DomEvent) -> None:
    if event.value:
        clip_line.container = [f"input value: {event.value!r}"]


async def on_copy(event: DomEvent) -> None:
    clip_log_line("copy event (user pressed Ctrl+C)")


async def on_cut(event: DomEvent) -> None:
    clip_log_line("cut event (user pressed Ctrl+X)")


paste_input.on_paste(on_paste)
paste_input.on_input(on_paste_input)
paste_input.on_copy(on_copy)
paste_input.on_cut(on_cut)

copy_btn = Button("Copy sample text")
read_btn = Button("Read clipboard", variant="ghost")


async def on_copy_click(event: DomEvent) -> None:
    try:
        await app.clipboard_write("Neony wrote this from Python!")
    except Exception as exc:
        clip_line.container = [f"write failed: {exc}"]
        clip_log_line(f"clipboard_write() failed: {exc}")
        return
    clip_line.container = ['wrote "Neony wrote this from Python!"']
    clip_log_line("clipboard_write() — verified via execCommand")


async def on_read_click(event: DomEvent) -> None:
    try:
        text = await app.clipboard_read()
    except Exception as exc:  # permission denied / no gesture
        clip_line.container = [f"read failed: {exc}"]
        clip_log_line(f"clipboard_read() failed: {exc}")
        return
    clip_line.container = [f"read: {text!r}"]
    clip_log_line("clipboard_read() — needs a user gesture")


copy_btn.on_click(on_copy_click)
read_btn.on_click(on_read_click)

clipboard_panel = Section(
    "Clipboard",
    "Paste into the field and the clipboard contents reach Python via "
    "the paste event (plain text + HTML, when the backend exposes it). "
    "Ctrl+C / Ctrl+X in the field fire copy/cut notifications. The "
    "buttons drive the system clipboard directly — writes use the "
    "synchronous execCommand path with an async clipboard attempt; "
    "reads poll the in-page async result, falling back to the OS "
    "clipboard tool (wl-paste / xclip) on Linux, where WebKitGTK "
    "has no readText. Both need a user gesture (a click is one), "
    "like the browser.",
    """inp.on_paste(lambda e: print(e.clipboard_text, e.clipboard_html))
inp.on_copy(lambda e: print("copy"))
await app.clipboard_write("hello")   # needs a gesture (a click is one)
text = await app.clipboard_read()    # needs a gesture too""",
    paste_input,
    clip_line,
    HStack(copy_btn, read_btn, gap="8px"),
    clip_log,
)

# ── tab: shortcuts ───────────────────────────────────────────────

shortcut_log = Text("", role="secondary")
b_chip, b_dot = StatusChip("Ctrl+B — bold")
g_chip, g_dot = StatusChip("Ctrl+G — glow")
d_chip, d_dot = StatusChip("Ctrl+D — dark")
k_chip, k_dot = StatusChip("Ctrl+K (Meta+K on macOS) — theme")

# Page-level registrations happen once `page` exists (below); the dots
# are wired in the handler factory there.

# ── tab: reactive ────────────────────────────────────────────────

count = Signal(0)
count_value = Text("0", size="40px", weight="bold")
count_value.bind_text(count)

heat = Signal(30)
heat_bar = Div(
    styles=Styles(
        height="14px",
        border_radius="7px",
        background_color=Color(var="--color-border"),
        transition="all 0.15s ease",
    )
)
heat_bar.bind_style(
    heat,
    "width",
    fmt=lambda n: f"{max(0, min(100, n))}%",
)
heat_bar.bind_style(
    heat,
    "background_color",
    fmt=lambda n: Color(rgb=(int(40 + 2.1 * max(0, min(100, n))), int(190 - 1.3 * max(0, min(100, n))), 120)),
)
heat_label = Text("heat: 30%", role="secondary")
heat_label.bind_text(heat, fmt=lambda n: f"heat: {n}%")

plus_btn = Button("+")
minus_btn = Button("-", variant="ghost")
plus_btn.on_click(lambda _e: heat.update(lambda n: max(0, min(100, n + 10))))
minus_btn.on_click(lambda _e: heat.update(lambda n: max(0, min(100, n - 10))))

# Computed: two signals, one derived value, one bound label.
first_name = Signal("")
last_name = Signal("")
first_input = Input(placeholder="First name")
last_input = Input(placeholder="Last name")
full_name = Computed(lambda: f"{first_name().strip()} {last_name().strip()}".strip())
full_echo = Text("", role="secondary")
full_echo.bind_text(full_name, fmt=lambda v: f"Computed full name: {v}" if v else "Type both names…")


async def on_first(event: DomEvent) -> None:
    first_name.set(event.value)


async def on_last(event: DomEvent) -> None:
    last_name.set(event.value)


first_input.on_input(on_first)
last_input.on_input(on_last)

# Effect: re-runs on dependency change, cleans up via dispose().
level = Signal(50)
level_text = Mono()
level_text.container = [f"Effect fired — level = {level()}"]
effect_slot = {"eff": None}


def level_sync() -> None:
    level_text.container = [f"Effect fired — level = {level()}"]


effect_slot["eff"] = effect(level_sync)
effect_btn = Button("Dispose effect", variant="ghost")
effect_state = Text("effect: running", role="secondary", size="12px")


async def on_effect_toggle(event: DomEvent) -> None:
    if effect_slot["eff"] is not None:
        effect_slot["eff"].dispose()
        effect_slot["eff"] = None
        effect_btn.label = "Restart effect"
        effect_state.text = "effect: disposed — level changes no longer sync"
    else:
        effect_slot["eff"] = effect(level_sync)
        effect_btn.label = "Dispose effect"
        effect_state.text = "effect: running"


effect_btn.on_click(on_effect_toggle)

level_up = Button("Level +5")
level_down = Button("Level -5", variant="ghost")
level_up.on_click(lambda _e: level.update(lambda n: max(0, min(100, n + 5))))
level_down.on_click(lambda _e: level.update(lambda n: max(0, min(100, n - 5))))

# bind_visible: a checkbox drives an element's display.
secret = Signal(True)
secret_block = Div(
    styles=Styles(
        border="1px solid var(--color-border)",
        border_radius="8px",
        padding="12px 16px",
        background_color=Color(var="--color-surface"),
    ),
    container=["This box's display is bound to a Signal."],
)
secret_block.bind_visible(secret)
secret_check = Checkbox("Visible", checked=True)


async def on_secret_toggle(event: DomEvent) -> None:
    secret.set(bool(event.value))


secret_check.on_change(on_secret_toggle)

reactive_panel = Section(
    "Reactive",
    "Signal, Computed and Effect with declarative bindings — no manual "
    "refresh calls. bind_text / bind_style / bind_visible follow their "
    "signal: bump the heat bar (width AND colour), type a name, toggle "
    "visibility, or dispose the effect and watch the level sync stop.",
    """count = Signal(0)
label.bind_text(count)

heat = Signal(30)
bar.bind_style(heat, "width", fmt=lambda n: f"{n}%")
bar.bind_style(heat, "background_color", fmt=colorize)

full = Computed(lambda: f"{first()} {last()}")
echo.bind_text(full)

box.bind_visible(flag)
eff = effect(sync)   # re-runs on dependency change
eff.dispose()        # stops it""",
    HStack(Text("Heat bar", weight="600"), Spacer(), minus_btn, plus_btn, gap="8px"),
    heat_bar,
    heat_label,
    Separator(),
    HStack(first_input, last_input, gap="8px"),
    full_echo,
    Separator(),
    HStack(Text("Effect", weight="600"), Spacer(), level_down, level_up, effect_btn, gap="8px"),
    level_text,
    effect_state,
    Separator(),
    secret_check,
    secret_block,
)

# ── tab: sidebar ─────────────────────────────────────────────────

sidebar = Sidebar(
    SidebarItem("Home", icon="🏠"),
    SidebarItem("Settings", icon="⚙️"),
    SidebarItem("Profile", icon="👤"),
    active_key="home",
    corner_radius="0px",
)
sidebar_title = Text("Home", weight="600", size="16px")
sidebar_pane = GlassPanel(
    sidebar_title,
    Text(
        "The Sidebar drives a content pane through its on_change event; the active item keeps the accent border.",
        role="secondary",
    ),
    gap="12px",
    padding="16px",
    radius="0px",
    grow=True,
)
sidebar_state = Text("active: home", role="secondary", size="12px")


def switch_pane(key: str) -> None:
    sidebar_title.text = key.title()
    sidebar_state.text = f"active: {key}"


sidebar.on_change(lambda e: switch_pane(e.value))

sidebar_panel = Section(
    "Sidebar",
    "A vertical navigation rail for frameless chrome layouts. active_key "
    "controls the highlighted item; on_change fires with the item's key. "
    "Glass-matched to the TitleBar — pair them in a frameless window.",
    """sidebar = Sidebar(
    SidebarItem("Home", icon="🏠"),
    SidebarItem("Settings", icon="⚙️"),
    active_key="home",
)
sidebar.on_change(lambda e: switch_pane(e.value))""",
    HStack(sidebar, sidebar_pane, gap="12px", align="stretch"),
    sidebar_state,
)

# ── tab: window ──────────────────────────────────────────────────

# Wayland forbids client-side window positioning (tao's
# set_outer_position is a no-op there), so the position buttons also
# resize — the size change proves set_bounds is working either way.
_ON_WAYLAND = "WAYLAND_DISPLAY" in os.environ and sys.platform.startswith("linux")

win_status = Text("Window state", role="secondary")
win_note = Text(
    "Hide auto-restores after 2s (the Show button lives inside the window, "
    "so a permanent hide would trap you). "
    + (
        "On Wayland window position is a no-op (the protocol forbids "
        "client-side positioning). Resize is a request: tiling WMs ignore "
        "it while the window is tiled — float the window (e.g. Win+F) "
        "for set_bounds/set_size to apply."
        if _ON_WAYLAND
        else "Position is in logical pixels from the top-left of the screen."
    ),
    role="secondary",
    size="12px",
)

hide_btn = Button("Hide", variant="ghost")
show_btn = Button("Show", variant="ghost")
focus_btn = Button("Focus", variant="ghost")
pos1_btn = Button("Compact @ (100, 100)")
pos2_btn = Button("Default @ (0, 0)", variant="ghost")


async def on_hide(event: DomEvent) -> None:
    await app.hide()
    win_status.text = "Window hidden — auto-restoring in 2s…"
    await asyncio.sleep(2)
    await app.show()
    win_status.text = "Window shown again (auto-restore)"


async def on_show(event: DomEvent) -> None:
    await app.show()
    win_status.text = "Window shown"


async def on_focus_click(event: DomEvent) -> None:
    await app.focus()
    win_status.text = "Window focused"


async def on_pos1(event: DomEvent) -> None:
    await app.set_bounds(100, 100, 440, 560)
    win_status.text = "set_bounds(100, 100, 440, 560) applied"


async def on_pos2(event: DomEvent) -> None:
    await app.set_bounds(0, 0, 560, 720)
    win_status.text = "set_bounds(0, 0, 560, 720) applied"


hide_btn.on_click(on_hide)
show_btn.on_click(on_show)
focus_btn.on_click(on_focus_click)
pos1_btn.on_click(on_pos1)
pos2_btn.on_click(on_pos2)

window_panel = Section(
    "Window State",
    "show / hide / focus move the window on screen; set_bounds positions "
    "it via tao (outer position) and resizes it. The status line also "
    "tracks the page's on_focus / on_blur lifecycle hooks (not emitted "
    "on every stack — Wayland/GTK focus events are backend-dependent).",
    """await app.show() / app.hide() / app.focus()
await app.set_bounds(x, y, w, h)   # outer position + inner size
page.on_focus(lambda: print("focused"))
page.on_blur(lambda: print("blurred"))""",
    win_status,
    HStack(hide_btn, show_btn, focus_btn, gap="8px"),
    HStack(pos1_btn, pos2_btn, gap="8px"),
    win_note,
)

# ── assemble ─────────────────────────────────────────────────────

page = Page(gap="0px", padding="0px", max_width="100%", fill=True, radius="12px")


# Page-level lifecycle hooks drive the Window tab status line.
async def on_page_focus() -> None:
    win_status.text = "Window focused"


async def on_page_blur() -> None:
    win_status.text = "Window lost focus (or hidden)"


page.on_focus(on_page_focus)
page.on_blur(on_page_blur)

# Window-level key events drive the Events tab's modifier lights —
# they respond wherever keys land (even while an input has focus),
# so no "focus the input first" step is needed.
page.on_keydown(on_mod_key)
page.on_keyup(on_mod_key)

# In-app shortcuts: window-level, fire even while an input has focus,
# on any tab.  Registered on the Page, so they work window-wide.
# The handler lights its dot, then dims it again after a beat.


async def shortcut_handler(dot: Div, message: str) -> None:
    set_dot(dot, True)
    shortcut_log.text = message
    # Auto-render only runs after the handler returns — the 0.4s flash
    # would be swallowed (ON → OFF inside one handler, never rendered).
    # An explicit render shows the lit state, then the handler returns
    # and the auto-render dims it.
    await app.render()
    await asyncio.sleep(0.4)
    set_dot(dot, False)


page.on_shortcut("Ctrl+B", lambda: shortcut_handler(b_dot, "Ctrl+B — bold"))
page.on_shortcut("Ctrl+G", lambda: shortcut_handler(g_dot, "Ctrl+G — glow"))
page.on_shortcut("Ctrl+D", lambda: shortcut_handler(d_dot, "Ctrl+D — dark"))
page.on_shortcut(
    {"darwin": "Meta+K", "default": "Ctrl+K"},
    lambda: shortcut_handler(k_dot, "Ctrl+K / Meta+K — theme"),
)

shortcuts_panel = Section(
    "Shortcuts",
    "Page-level keybindings that fire anywhere in the window — even "
    "while an input has focus, and on any tab. Register a single "
    "combo or a per-platform dict (Ctrl+Meta on macOS vs Ctrl on "
    "Linux/Windows). Modifiers must match exactly; the key matches "
    "case-insensitively. Try them from here or any other tab:",
    """page.on_shortcut("Ctrl+B", bold)
page.on_shortcut({"darwin": "Meta+K", "default": "Ctrl+K"}, theme)
# handlers receive no arguments; sync or async""",
    shortcut_log,
    HStack(b_chip, g_chip, d_chip, k_chip, gap="16px"),
)

tabs = Tabs(glass=True)
tabs.add("Buttons", buttons_panel)
tabs.add("Inputs", inputs_panel)
tabs.add("Checks", checks_panel)
tabs.add("Layout", layout_panel)
tabs.add("Type", typography_panel)
tabs.add("Glass", glass_panel)
tabs.add("Icon", icon_panel)
tabs.add("Events", events_panel)
tabs.add("Drop", drop_panel)
tabs.add("Clipboard", clipboard_panel)
tabs.add("Shortcuts", shortcuts_panel)
tabs.add("Reactive", reactive_panel)
tabs.add("Sidebar", sidebar_panel)
tabs.add("Window", window_panel)

# ── assemble: transparent TitleBar over a solid content stage ─────

titlebar = TitleBar("Neony — Component Gallery", icon=_ICON_URL)

# The content stage uses the plain theme background — only the titlebar
# above it stays transparent, so the desktop shows through the chrome
# while the docs/text get a solid, readable backdrop.
content = Div(
    styles=Styles(
        flex_grow="1",
        min_height="0",
        overflow="auto",
        background_color=Color(var="--color-bg"),
    ),
    container=[VStack(header, tabs, gap="16px", padding="24px").build()],
)

# grow=1 makes the chrome stack fill the window; the content stage then
# grows to fill the space below the titlebar.
page.add(VStack(titlebar, content, gap="0px", align="stretch", grow=1))


def main() -> None:
    app.run(page)


if __name__ == "__main__":
    main()
