#!/usr/bin/env python3
"""Neony component gallery — every component with docs and code samples.

Each tab pairs a live component demo with a short description and the
Python snippet that produced it, so the gallery doubles as a reference.

Showcases: Button variants, Input types, Checkbox state, form controls
(radio groups, switches, selects, combo boxes, sliders, progress bars),
layout primitives (HStack/Flex/Spacer), typography roles, frosted
glass, window icon, rich event payloads (modifiers / coordinates /
wheel), file drag-and-drop, clipboard events + API, in-app shortcuts,
reactive primitives (Signal / Computed / Effect / bindings), the
Sidebar component, and window-state control (show / hide / focus /
set_bounds).

Signals and ``bind_*`` cover direct state synchronization in the examples;
named ``on_*`` handlers are retained where event payloads, async work, or
multiple side effects are required.

Usage:
    python demo_gallery.py
"""

import asyncio
import os
import sys

from neony.application import Config, NeonApplication, Page, Theme, WebViewConfig, WindowConfig
from neony.application.elements import (
    Avatar,
    Badge,
    Button,
    Card,
    Checkbox,
    ComboBox,
    Component,
    Dialog,
    DialogAction,
    Dropdown,
    Flex,
    GlassPanel,
    Heading,
    HStack,
    Icon,
    Image,
    Input,
    Menu,
    Pane,
    Progress,
    PromptDialog,
    Radio,
    RadioGroup,
    Select,
    Separator,
    Sidebar,
    Slider,
    Spacer,
    Switch,
    Text,
    TitleBar,
    Tooltip,
    Tree,
    TreeNode,
    VStack,
)
from neony.dom import (
    Animation,
    Color,
    Computed,
    Div,
    DOMElement,
    DomEvent,
    KeyFrame,
    Props,
    Signal,
    Styles,
    batch,
    effect,
    untrack,
)

# Frameless + transparent: the gallery gets its own glass TitleBar, and
# the desktop shows through the frosted chrome.
app = NeonApplication(
    Config(
        window=WindowConfig(
            title="Neony — Component Gallery",
            width=1000,
            height=640,
            decorations=False,
            transparent=True,
        ),
        webview=WebViewConfig(devtools=True),
    )
)

_BACKGROUND_URL = "https://harcic.is-a.dev/resource/backgrounds/8.webp"
_ICON_URL = "https://harcic.is-a.dev/resource/favicon.svg"

_MONO = "ui-monospace, 'SF Mono', Menlo, Consolas, monospace"

# Shared across tabs: bumped in the Reactive tab, observed in Forms.
heat = Signal(30)


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

theme_btn = Button("Light mode", variant="ghost")


async def on_theme_click(_event: DomEvent) -> None:
    app.theme.toggle()
    await app.sync_theme()
    theme_btn.label = Theme.mode_label(app.theme.mode)


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

# Signal-driven counter: the click handler only bumps the signal; the
# label follows via bind_text — the reactive way to hold UI state.
clicks = Signal(0)
clicks_btn = Button("Click me")
clicks_btn.on_click(lambda _e: clicks.update(lambda n: n + 1))
clicks_text = Text("0 clicks", role="secondary")
clicks_text.bind_text(clicks, fmt=lambda n: f"{n} clicks")

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
    "base look while keeping the feedback. The counter holds its state "
    "in a Signal — the click only bumps it, bind_text redraws the label.",
    """Button("Primary Action")
Button("Ghost Button", variant="ghost")
Button("Delete", variant="danger")
Button("Disabled", disabled=True)
Button("Custom").reset_styles(
    Styles(background_color=Color(hex="#2fa89a"), ...))

clicks = Signal(0)
btn.on_click(lambda _e: clicks.update(lambda n: n + 1))
label.bind_text(clicks, fmt=lambda n: f"{n} clicks")""",
    primary_btn,
    ghost_btn,
    danger_btn,
    disabled_btn,
    custom_btn,
    Separator(),
    clicks_btn,
    clicks_text,
)

# ── tab: inputs ──────────────────────────────────────────────────

text_input = Input(placeholder="Your name…")
text_echo = Text("", role="secondary")
text_value = Signal("")
text_input.bind_value(text_value)
text_echo.bind_text(text_value, fmt=lambda value: f"Hello, {value}!" if value else "")

password_input = Input(placeholder="Password", type="password")
password_echo = Text("", role="secondary")
password_value = Signal("")
password_input.bind_value(password_value)
password_echo.bind_text(password_value, fmt=lambda value: f"Length: {len(value)}" if value else "")

email_input = Input(placeholder="Email", type="email")
email_echo = Text("", role="secondary")
email_value = Signal("")
email_input.bind_value(email_value)
email_echo.bind_text(email_value, fmt=lambda value: f"Email: {value}" if value else "")

inputs_panel = Section(
    "Inputs",
    "Text, password and email fields. Each input binds its value to a "
    "Signal and each echo binds declaratively to that Signal with a "
    "formatting function.",
    """name = Signal("")
text_input.bind_value(name)
text_echo.bind_text(name, fmt=lambda v: f"Hello, {v}!" if v else "")

pwd = Input(placeholder="Password", type="password")   # email / number …
pwd.bind_value(password)""",
    text_input,
    text_echo,
    password_input,
    password_echo,
    email_input,
    email_echo,
)

# ── tab: checks ──────────────────────────────────────────────────

# The signals are the single source of truth: each checkbox is bound
# two-way, "Select all" is a Computed driven by a read-only binding,
# and the status line is a bound text — no manual refresh calls.
FOODS = ["Pizza", "Tacos", "Ramen"]
food_flags = {name: Signal(False) for name in FOODS}
food_checks = [Checkbox(name).bind_value(food_flags[name]) for name in FOODS]

all_selected = Computed(lambda: all(food_flags[name]() for name in FOODS))
check_all = Checkbox("Select all")
check_all.bind_value(all_selected)


def on_check_all(event: DomEvent) -> None:
    for flag in food_flags.values():
        flag.set(bool(event.value))


check_all.on_change(on_check_all)
check_status = Text("", role="secondary")
check_status.bind_text(Computed(lambda: f"{sum(1 for name in FOODS if food_flags[name]())} of {len(FOODS)} selected"))

checks_panel = Section(
    "Checkboxes",
    "Custom-styled toggles with a change event. Signals are the single "
    "source of truth: each food checkbox is bound two-way via "
    'bind_value, "Select all" is a Computed bound read-only, and '
    "the status line is a bound text — nothing refreshes by hand.",
    """flag = Signal(False)
cb = Checkbox("Pizza")
cb.bind_value(flag)      # two-way: toggling writes the signal

all_selected = Computed(lambda: all(f[name]() for name in FOODS))
check_all.bind_value(all_selected)
status.bind_text(Computed(lambda: f"{n} of 3 selected"))""",
    check_all,
    *food_checks,
    check_status,
)

# ── tab: forms ───────────────────────────────────────────────────

meal_group = RadioGroup(
    Radio("Pizza", value="pizza"),
    Radio("Tacos", value="tacos"),
    Radio("Ramen", value="ramen"),
)
meal = Signal("pizza")
meal_group.bind_selected(meal)
meal_echo = Text("", role="secondary")
meal_echo.bind_text(meal, fmt=lambda value: f"Picked: {value}")

wifi = Signal(False)
wifi_switch = Switch("Wi-Fi")
wifi_switch.bind_value(wifi)
wifi_status = Text("", role="secondary")
wifi_status.bind_text(wifi, fmt=lambda enabled: "On" if enabled else "Off")

size_select = Select(
    "Size",
    options=[("s", "Small"), ("m", "Medium"), ("l", "Large")],
    placeholder="Pick a size…",
    value="m",
)
size = Signal("m")
size_select = Select(
    "Size",
    options=[("s", "Small"), ("m", "Medium"), ("l", "Large")],
    placeholder="Pick a size…",
    value="m",
)
size_select.bind_value(size)
size_echo = Text("", role="secondary")
size_echo.bind_text(size, fmt=lambda value: f"Selected: {value}")

tag_combobox = ComboBox("Tag", options=["work", "personal", "travel"], placeholder="Type or pick…")
tag = Signal("")
tag_combobox = ComboBox("Tag", options=["work", "personal", "travel"], placeholder="Type or pick…")
tag_combobox.bind_value(tag)
tag_echo = Text("", role="secondary")
tag_echo.bind_text(tag, fmt=lambda value: f"Tag: {value}" if value else "")

# One signal drives three widgets: slider, readout and progress bar.
volume = Signal(40)
volume_slider = Slider("Volume (stepped)", min=0, max=100, step=5, value=40)
volume_slider.bind_value(volume)
volume_readout = Mono()
volume_readout.bind_text(volume, fmt=lambda value: f"{value:.0f}%")
volume_progress = Progress(label="The progress bar follows the same signal")
volume_progress.bind_value(volume)

# step="any" → stepless: every float is reachable, the fill follows the
# thumb instantly while dragging and glides on programmatic sets.
smooth_volume = Signal(40.0)
smooth_slider = Slider("Volume (continuous)", min=0, max=100, step="any", value=40)
smooth_slider.bind_value(smooth_volume)
smooth_readout = Mono()
smooth_readout.bind_text(smooth_volume, fmt=lambda v: f"{v:.1f}%")

# Cross-tab reactivity: this readout follows the `heat` signal that the
# Reactive tab's buttons drive — switch tabs and bump it there.
heat_share = Text("", role="secondary", size="12px")
heat_share.bind_text(heat, fmt=lambda n: f"shared heat signal (from the Reactive tab): {n}%")

load = Signal(35)
load_bar = Progress("Downloading…", value=35)
load_bar.bind_value(load)
scan_bar = Progress("Scanning…", indeterminate=True)
advance_btn = Button("+15%", variant="ghost").on_click(lambda _event: load.update(lambda value: min(100, value + 15)))

forms_panel = Section(
    "Forms",
    "Radio groups, switches, dropdowns, combo boxes, sliders and "
    "progress bars. State is owned by the component: programmatic "
    "writes never fire callbacks, user-driven events carry "
    'source == "user". Sliders draw their own fill track; step="any" '
    "makes one stepless. The volume slider, its readout and a progress "
    "bar all share one Signal via bind_value — drag and watch the "
    "others follow. The heat readout at the bottom follows the Reactive "
    "tab's shared signal.",
    """group = RadioGroup(Radio("Pizza"), Radio("Tacos"))
group.on_change(lambda e: print(e.value))  # value string

sw = Switch("Wi-Fi")
sw.on_change(lambda e: print(e.value))  # bool

sel = Select("Size", options=[("s", "Small"), ("m", "Medium")],
             placeholder="Pick…")
sel.on_change(lambda e: print(e.value))  # option value

box = ComboBox("Tag", options=["work", "personal"])
box.on_input(lambda e: print(e.value))  # live text

vol = Signal(40)
slider.bind_value(vol)                  # two-way: drag writes back
readout.bind_text(vol, fmt=lambda v: f"{v:.0f}%")
follow = Progress(); follow.bind_value(vol)  # write-only follower

bar = Progress(value=35)
bar.value = 50  # fill glides; no callback
Progress(indeterminate=True)  # sliding sweep animation""",
    meal_group,
    meal_echo,
    Separator(),
    wifi_switch,
    wifi_status,
    Separator(),
    size_select,
    size_echo,
    Separator(),
    tag_combobox,
    tag_echo,
    Separator(),
    volume_slider,
    volume_readout,
    volume_progress,
    smooth_slider,
    smooth_readout,
    heat_share,
    Separator(),
    load_bar,
    scan_bar,
    advance_btn,
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
    "HStack rows with Spacer pushing content; Flex gives full control, "
    "including wrapping. VStack stacks vertically, Separator divides, "
    "GlassPanel frosts.",
    """HStack(Text("Title"), Spacer(), Button("Edit"), gap="8px")
Flex(*items, direction="row", wrap="wrap", gap="8px")
VStack(a, b, gap="12px")
Separator()
GlassPanel("Frosted", role="accent")""",
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
    """Heading("Title", level=1)   # level 1-6
Text("Body copy")
Text("Muted copy", role="secondary")
Text("Danger", role="danger")
Text("OK", role="success")
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
glass_value = Signal("")
glass_input.bind_value(glass_value)
glass_input_echo.bind_text(glass_value, fmt=lambda value: f"Typed: {value}" if value else "")

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
TitleBar("My App", icon=Icon.image("https://harcic.is-a.dev/resource/favicon.svg"))

# Decorated — the OS window chrome shows it:
launch(page, title="My App", icon="icon.png")
# or: Config(window=WindowConfig(title="My App", icon="icon.png"))

# Runtime swap (either mode):
await app.set_icon("icon.png")

# Local resources:
from neony.application import file_url, data_url
GlassPanel(background=file_url("bg.png"))
TitleBar(icon=Icon.image(data_url("logo.svg")))""",
    VStack(
        Text("Live: the favicon in the titlebar above uses TitleBar(icon=...).", role="secondary"),
        Text(
            "For decorated windows the taskbar / titlebar icon comes from "
            "WindowConfig.icon; TitleBar(icon=...) only affects frameless chrome.",
            role="secondary",
        ),
        gap="8px",
    ),
)

# ── tab: events ──────────────────────────────────────────────────

# Mouse tracker: mousedown anywhere inside the zone (even on its text
# labels) bubbles to this bubble_events Div.  The DomEvent carries the
# viewport (x/y) and element-relative (offset_x/offset_y) coordinates.
tracker_text = Text("Click anywhere in this box", role="secondary")
click_info = Signal("—")
click_pos = Mono()
click_pos.bind_text(click_info)

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
tracker.bubble_events = True


async def on_tracker_down(event: DomEvent) -> None:
    click_info.set(f"down at ({event.x:.0f}, {event.y:.0f})  offset ({event.offset_x:.0f}, {event.offset_y:.0f})")


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
wheel_total = Signal(0.0)
wheel_readout = Signal("dx: —   dy: —   total: 0px")
wheel_delta = Mono()
wheel_delta.bind_text(wheel_readout)
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
wheel_zone.bubble_events = True


async def on_wheel(event: DomEvent) -> None:
    # delta_mode: 0 = pixels, 1 = lines (x16), 2 = pages (x256).
    factor = 16 ** (event.delta_mode or 0)
    px = (event.delta_y or 0) * factor
    wheel_total.update(lambda total: total + px)
    wheel_readout.set(
        f"dy: {event.delta_y:+.0f} (mode {event.delta_mode})   dx: {event.delta_x:+.0f}   total: {wheel_total():+.0f}px"
    )


wheel_zone.on_wheel(on_wheel)

# Pointer move: live tracking.  movement_x/y are the delta since the
# last pointermove — no manual position bookkeeping needed — and
# pointer_type tells mouse / pen / touch apart.  Pointermove rides the
# deferred render path, so the readout coalesces to one render per
# frame instead of one per event.
pointer_info = Signal("—")
pointer_readout = Mono()
pointer_readout.bind_text(pointer_info)
pointer_zone = Div(
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
    container=[pointer_readout],
)
pointer_zone.bubble_events = True


async def on_pointer_move(event: DomEvent) -> None:
    pointer_info.set(
        f"({event.x:.0f}, {event.y:.0f})   "
        f"movement ({event.movement_x:+.0f}, {event.movement_y:+.0f})   "
        f"{event.pointer_type or '?'}"
    )


pointer_zone.on_pointermove(on_pointer_move)

events_panel = Section(
    "Rich Events",
    "Every delegated event carries the full payload: modifier keys "
    "(ctrl/shift/alt/meta), viewport and element-relative mouse "
    "coordinates, wheel deltas, and pointer movement — live delta and "
    "device type. Click the box, hold modifiers while typing, scroll "
    "the zone, move the pointer across the bottom box.",
    """div.on_mousedown(lambda e: f"{e.x}, {e.y} — {e.offset_x}, {e.offset_y}")
div.on_keydown(lambda e: e.ctrl_key or e.meta_key)
div.on_wheel(lambda e: f"dx: {e.delta_x}  dy: {e.delta_y}")
div.on_pointermove(lambda e: f"{e.movement_x}, {e.movement_y} — {e.pointer_type}")""",
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
    pointer_zone,
)

# ── tab: animations ──────────────────────────────────────────────

# Typed @keyframes — chainable builder; register_keyframe injects the
# CSS into <style id="neony-keyframes"> in every window (later-wins on
# name collision).
spin = KeyFrame("spin").set("0%", Props(transform="rotate(0deg)")).set("100%", Props(transform="rotate(360deg)"))
app.register_keyframe(spin)

fade_slide = (
    KeyFrame("fade-slide")
    .set("0%", Props(opacity=0, transform="translateY(8px)"))
    .set("100%", Props(opacity=1, transform="translateY(0)"))
)
app.register_keyframe(fade_slide)

# Spinner: a border ring spun by the keyframe above.  The Animation
# model references the KeyFrame by name — the browser resolves the
# @keyframes block automatically.
spinner = Div(
    styles=Styles(
        width="36px",
        height="36px",
        border="3px solid var(--color-border)",
        border_top="3px solid var(--color-accent)",
        border_radius="50%",
        animation=Animation(name="spin", duration="1s", timing="linear", iteration_count="infinite"),
    )
)
spin_state = Text("", size="12px", role="secondary")
paused = Signal(False)
spin_state.bind_text(paused, fmt=lambda is_paused: "paused" if is_paused else "running")


async def on_spin_toggle(_event: DomEvent) -> None:
    anim = spinner.styles.animation
    is_paused = paused()
    if isinstance(anim, Animation):
        spinner.styles.animation = anim.model_copy(update={"play_state": "running" if is_paused else "paused"})
    paused.set(not is_paused)


spin_toggle = Button("Pause", variant="ghost")
spin_toggle.on_click(on_spin_toggle)

# A card that plays its enter animation once, on mount.
enter_card = Div(
    styles=Styles(
        border="1px solid var(--color-border)",
        border_radius="8px",
        padding="16px",
        background_color=Color(var="--color-surface"),
        animation=Animation(name="fade-slide", duration="0.4s", timing="ease-out"),
    ),
    container=["Fades + slides in on mount"],
)

animations_panel = Section(
    "Animations",
    "Typed @keyframes: build a KeyFrame with the chainable .set() "
    "builder, register it once, and reference it from any element's "
    "Animation model — multi-stop, named, and injected into a global "
    "<style> like the theme. The spinner loops forever; the card plays "
    "a one-shot fade-slide on mount. Pause/resume toggles play-state.",
    """spin = KeyFrame("spin").set("0%", Props(transform="rotate(0deg)"))
                     .set("100%", Props(transform="rotate(360deg)"))
app.register_keyframe(spin)
icon.styles.animation = Animation(name="spin", duration="1s",
                                  timing="linear",
                                  iteration_count="infinite")
icon.styles.animation = anim.model_copy(update={"play_state": "paused"})  # pause/resume

fade = KeyFrame("fade-slide").set("0%", Props(opacity=0, transform="translateY(8px)"))
card.styles.animation = Animation(name="fade-slide", duration="0.5s")""",
    HStack(spinner, spin_state, spin_toggle, gap="12px", align="center"),
    enter_card,
)

# ── tab: drop ────────────────────────────────────────────────────

drop_hint = Text("Drop files anywhere in this box", role="secondary")
dragging = Signal(False)
drop_files = Signal("")
drop_hint.bind_text(dragging, fmt=lambda active: "Release to drop" if active else "Drop files anywhere in this box")
drop_list = Mono(size="12px")
drop_list.bind_text(drop_files)

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
drop_zone.bubble_events = True
drop_zone.bind_style(
    dragging,
    "border",
    fmt=lambda active: "2px dashed var(--color-accent)" if active else "2px dashed var(--color-border)",
)
drop_zone.bind_style(
    dragging,
    "background_color",
    fmt=lambda active: Color(var="--color-surface") if active else None,
)


def fmt_size(size: int) -> str:
    """Human-readable byte count."""
    if size >= 1024 * 1024:
        return f"{size / 1024 / 1024:.1f} MB"
    if size >= 1024:
        return f"{size / 1024:.1f} KB"
    return f"{size} B"


async def on_drop_over(_event: DomEvent) -> None:
    dragging.set(True)


async def on_drop_leave(_event: DomEvent) -> None:
    dragging.set(False)


async def on_drop(event: DomEvent) -> None:
    dragging.set(False)
    if not event.drop_files:
        drop_files.set("(no files — on WKWebView the file path is empty)")
        return
    lines = [f"{file['name']}   ({fmt_size(file['size'])}, {file['type']})" for file in event.drop_files]
    lines.append("")
    lines.extend(f"path: {file['path'] or '<unavailable>'}" for file in event.drop_files)
    drop_files.set("\n".join(lines))


drop_zone.on_dragover(on_drop_over).on_dragleave(on_drop_leave).on_drop(on_drop)

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
clip_history = Signal("")
clip_log.bind_text(clip_history)
paste_input = Input(placeholder="Paste (Ctrl+V) into this field…")
clip_value = Signal("")
clip_line = Mono(size="12px")
clip_line.bind_text(clip_value)
clip_entries: list[str] = []


def clip_log_line(line: str) -> None:
    """Keep the last 4 log lines in Signal state."""
    clip_entries.append(line)
    clip_history.set("\n".join(clip_entries[-4:]))


async def on_paste(event: DomEvent) -> None:
    # clipboard_text may be None on some backends — the input's own
    # value (updated by the input event right after) is the fallback.
    if event.clipboard_text is None:
        clip_value.set("clipboard_text: <not exposed by this backend>")
    else:
        clip_value.set(
            f"clipboard_text: {event.clipboard_text!r}"
            + (f"  html: {event.clipboard_html!r}" if event.clipboard_html else "")
        )
    clip_log_line("paste event — clipboard carried into Python")


async def on_paste_input(event: DomEvent) -> None:
    if event.value:
        clip_value.set(f"input value: {event.value!r}")


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
        clip_value.set(f"write failed: {exc}")
        clip_log_line(f"clipboard_write() failed: {exc}")
        return
    clip_value.set('wrote "Neony wrote this from Python!"')


async def on_read_click(event: DomEvent) -> None:
    try:
        text = await app.clipboard_read()
    except Exception as exc:  # permission denied / no gesture
        clip_value.set(f"read failed: {exc}")
        clip_log_line(f"clipboard_read() failed: {exc}")
        return
    clip_value.set(f"read: {text!r}")


copy_btn.on_click(on_copy_click)
read_btn.on_click(on_read_click)

clipboard_panel = Section(
    "Clipboard",
    "Clipboard events carry data into Python: paste delivers "
    "clipboard_text / clipboard_html, copy / cut fire as notifications. "
    "The write/read API lives in the backend (no user gesture needed to "
    "write); read still needs the window focused.",
    """inp.on_paste(lambda e: print(e.clipboard_text, e.clipboard_html))
inp.on_copy(lambda e: print("copy"))
inp.on_cut(lambda e: print("cut"))
await app.clipboard_write("hello")
text = await app.clipboard_read()""",
    paste_input,
    clip_line,
    HStack(copy_btn, read_btn, gap="8px"),
    clip_log,
)

# ── tab: shortcuts ───────────────────────────────────────────────

shortcut_message = Signal("")
shortcut_log = Text("", role="secondary")
shortcut_log.bind_text(shortcut_message)
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


class HeatBar(Component):
    """Demo-local signal-driven heat bar."""

    def __init__(self, value: Signal, *, height: str = "14px") -> None:
        super().__init__()
        self._root = Div(
            styles=Styles(
                height=height,
                border_radius="7px",
                background_color=Color(var="--color-border"),
                transition="all 0.15s ease",
            )
        )
        self._root.bind_style(value, "width", fmt=lambda number: f"{max(0, min(100, number))}%")
        self._root.bind_style(value, "background_color", fmt=self._color)

    @staticmethod
    def _color(number: int | float) -> Color:
        number = max(0, min(100, number))
        return Color(rgb=(int(40 + 2.1 * number), int(190 - 1.3 * number), 120))


heat_bar = HeatBar(heat)
heat_label = Text("heat: 30%", role="secondary")
heat_label.bind_text(heat, fmt=lambda n: f"heat: {n}%")

plus_btn = Button("+")
minus_btn = Button("-", variant="ghost")
plus_btn.on_click(lambda _e: heat.update(lambda n: max(0, min(100, n + 10))))
minus_btn.on_click(lambda _e: heat.update(lambda n: max(0, min(100, n - 10))))

# Computed: two signals, one derived value, one bound label.
first_name = Signal("")
last_name = Signal("")
first_input = Input(placeholder="First name").bind_value(first_name)
last_input = Input(placeholder="Last name").bind_value(last_name)
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
level_log = Signal(f"Effect fired — level = {level()}")
level_text = Mono()
level_text.bind_text(level_log)
effect_slot = {"eff": None}
running = Signal(True)
effect_state = Text("", role="secondary", size="12px")
effect_state.bind_text(
    running,
    fmt=lambda active: "effect: running" if active else "effect: disposed — level changes no longer sync",
)


def level_sync() -> None:
    level_log.set(f"Effect fired — level = {level()}")


effect_slot["eff"] = effect(level_sync)
effect_btn = Button("Dispose effect", variant="ghost")


async def on_effect_toggle(_event: DomEvent) -> None:
    if running():
        current = effect_slot["eff"]
        if current is not None:
            current.dispose()
        effect_slot["eff"] = None
        running.set(False)
        effect_btn.label = "Restart effect"
    else:
        effect_slot["eff"] = effect(level_sync)
        running.set(True)
        effect_btn.label = "Dispose effect"


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
secret_check = Checkbox("Visible", checked=True).bind_value(secret)

# batch(): two signals changed together flush ONE effect run.
batch_a = Signal(0)
batch_b = Signal(0)
batch_runs = Signal(0)
batch_count = Mono()
batch_count.bind_text(batch_runs, fmt=lambda runs: f"effect runs: {runs}  (a={batch_a()}, b={batch_b()})")


def batch_sync() -> None:
    batch_a()
    batch_b()
    batch_runs.update(lambda runs: runs + 1)


batch_effect = effect(batch_sync)
batch_single_btn = Button("a + 1", variant="ghost")
batch_both_btn = Button("a + 1, b + 1 inside batch()", variant="ghost")


async def on_batch_single(_event: DomEvent) -> None:
    batch_a.update(lambda n: n + 1)


async def on_batch_both(_event: DomEvent) -> None:
    with batch():
        batch_a.update(lambda n: n + 1)
        batch_b.update(lambda n: n + 1)


batch_single_btn.on_click(on_batch_single)
batch_both_btn.on_click(on_batch_both)

# untrack(): reading a signal inside an effect without subscribing.
untrack_tracked = Signal(0)
untrack_ignored = Signal(0)
untrack_runs = Signal(0)
untrack_count = Mono()
untrack_count.bind_text(
    Computed(
        lambda: (
            f"effect runs: {untrack_runs()}  (tracked={untrack_tracked()}, "
            f"ignored={untrack_ignored()} read via untrack — no subscription)"
        )
    )
)


def untrack_sync() -> None:
    untrack_tracked()
    untrack_runs.update(lambda runs: runs + 1)
    untrack(untrack_ignored.get)


untrack_effect = effect(untrack_sync)
untrack_track_btn = Button("tracked + 1", variant="ghost")
untrack_ignore_btn = Button("ignored + 1 (untracked — no re-run)", variant="ghost")
untrack_track_btn.on_click(lambda _e: untrack_tracked.update(lambda n: n + 1))
untrack_ignore_btn.on_click(lambda _e: untrack_ignored.update(lambda n: n + 1))

# bind_attr: a signal drives an HTML attribute (the button's disabled).
busy = Signal(False)
busy_btn = Button("Save")
busy_btn.bind_attr(busy, "disabled")
busy_state = Text("busy: false — the disabled attribute follows the signal", role="secondary")
busy_state.bind_text(busy, fmt=lambda b: f"busy: {b} — disabled={' ' if b else ' not '}set on the button")
busy_toggle = Button("Toggle busy", variant="ghost")
busy_toggle.on_click(lambda _e: busy.update(lambda b: not b))

# Computed chain: two derived values, one bound label.
price = Signal(10.0)
qty = Signal(2)
rate = Signal(0.9)
subtotal = Computed(lambda: price() * qty())
total = Computed(lambda: subtotal() * rate())
price_up = Button("price +1", variant="ghost")
price_down = Button("price -1", variant="ghost")
qty_up = Button("qty +1", variant="ghost")
qty_down = Button("qty -1", variant="ghost")
rate_up = Button("rate +0.1", variant="ghost")
rate_down = Button("rate -0.1", variant="ghost")
price_up.on_click(lambda _e: price.update(lambda v: v + 1))
price_down.on_click(lambda _e: price.update(lambda v: max(0.0, v - 1)))
qty_up.on_click(lambda _e: qty.update(lambda v: v + 1))
qty_down.on_click(lambda _e: qty.update(lambda v: max(1, v - 1)))
rate_up.on_click(lambda _e: rate.update(lambda v: min(1.0, v + 0.1)))
rate_down.on_click(lambda _e: rate.update(lambda v: max(0.1, v - 0.1)))
total_text = Text("", size="16px", weight="600")
total_text.bind_text(
    total,
    fmt=lambda v: f"total: ¥{v:.2f}   (subtotal ¥{subtotal():.2f} x rate {rate():.1f})",
)

# bind_value: signal ↔ component value, both ways.
name_signal = Signal("")
bind_input = Input(placeholder="Type — the signal follows every keystroke…")
bind_input.bind_value(name_signal)
bind_echo_one = Text("", role="secondary")
bind_echo_two = Text("", role="secondary")
bind_echo_one.bind_text(name_signal, fmt=lambda v: f"echo 1: {v}")
bind_echo_two.bind_text(name_signal, fmt=lambda v: f"echo 2: {v}")
bind_set_btn = Button("Set signal → component", variant="ghost")
bind_set_btn.on_click(lambda _e: name_signal.set("written from the signal side"))

reactive_panel = Section(
    "Reactive",
    "Signal, Computed and Effect with declarative bindings — no manual "
    "refresh calls. bind_text / bind_style / bind_visible / bind_attr "
    "/ bind_value follow their signal; batch() coalesces writes into "
    "one flush, untrack() reads without subscribing, computed chains "
    "compose. The heat bar is shared across tabs — bump it here, watch "
    "the Forms tab.",
    """count = Signal(0)
label.bind_text(count)

heat = Signal(30)
bar.bind_style(heat, "width", fmt=lambda n: f"{n}%")
bar.bind_style(heat, "background_color", fmt=colorize)

full = Computed(lambda: f"{first()} {last()}")
echo.bind_text(full)

box.bind_visible(flag)
eff = effect(sync)   # re-runs on dependency change
eff.dispose()        # stops it

with batch():        # several writes → ONE effect run
    a.set(1); b.set(2)
untrack(ignored.get) # read without subscribing

btn.bind_attr(busy, "disabled")            # signal → attribute
total = Computed(lambda: subtotal() * rate())  # chains compose

inp.bind_value(name) # two-way: signal ↔ component value""",
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
    Separator(),
    HStack(Text("batch()", weight="600"), Spacer(), batch_single_btn, batch_both_btn, gap="8px"),
    batch_count,
    Separator(),
    HStack(Text("untrack()", weight="600"), Spacer(), untrack_track_btn, untrack_ignore_btn, gap="8px"),
    untrack_count,
    Separator(),
    HStack(Text("bind_attr", weight="600"), Spacer(), busy_toggle, gap="8px"),
    HStack(busy_btn, busy_state, gap="12px", align="center"),
    Separator(),
    HStack(
        Text("Computed chain", weight="600"),
        Spacer(),
        price_down,
        price_up,
        qty_down,
        qty_up,
        rate_down,
        rate_up,
        gap="8px",
    ),
    total_text,
    Separator(),
    bind_input,
    bind_echo_one,
    bind_echo_two,
    HStack(Spacer(), bind_set_btn, gap="8px"),
)

# ── tab: sidebar ─────────────────────────────────────────────────

home_pane = GlassPanel(
    Heading("Home", level=3),
    Text("Home content — the Sidebar owns this pane.", role="secondary"),
    gap="12px",
    padding="16px",
    radius="0px",
    grow=True,
)
settings_pane = GlassPanel(
    Heading("Settings", level=3),
    Text("Settings content — select another entry to switch panes.", role="secondary"),
    gap="12px",
    padding="16px",
    radius="0px",
    grow=True,
)
profile_pane = GlassPanel(
    Heading("Profile", level=3),
    Text("Profile content — pane state remains mounted while hidden.", role="secondary"),
    gap="12px",
    padding="16px",
    radius="0px",
    grow=True,
)

active_pane = Signal("home")
sidebar = Sidebar(
    Pane("Home", key="home", icon=Icon.glyph("🏠"), panel=home_pane),
    Pane("Settings", key="settings", icon=Icon.glyph("⚙️"), panel=settings_pane),
    Pane("Profile", key="profile", icon=Icon.glyph("👤"), panel=profile_pane),
    corner_radius="0px",
)
sidebar.bind_selected(active_pane)
sidebar_state = Text("", role="secondary", size="12px")
sidebar_state.bind_text(active_pane, fmt=lambda key: f"active: {key}")

sidebar_panel = Section(
    "Sidebar",
    "A Sidebar can own its content panes. Pane keys are explicit, "
    "selected state binds to a Signal, and clicking an item switches "
    "the mounted pane without a hand-written mapping or switch function.",
    """active = Signal("home")
sidebar = Sidebar(
    Pane("Home", key="home", icon=Icon.glyph("🏠"), panel=home_panel),
    Pane("Settings", key="settings", icon=Icon.glyph("⚙️"), panel=settings_panel),
)
sidebar.bind_selected(active)
state.bind_text(active, fmt=lambda key: f"active: {key}")""",
    sidebar,
    sidebar_state,
)

# ── tab: window ──────────────────────────────────────────────────

# Wayland forbids client-side window positioning (tao's
# set_outer_position is a no-op there), so the position buttons also
# resize — the size change proves set_bounds is working either way.
_ON_WAYLAND = "WAYLAND_DISPLAY" in os.environ and sys.platform.startswith("linux")

win_state = Signal("Window state")
win_status = Text("", role="secondary")
win_status.bind_text(win_state)
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
    win_state.set("Window hidden — auto-restoring in 2s…")
    await asyncio.sleep(2)
    await app.show()
    win_state.set("Window shown again (auto-restore)")


async def on_show(event: DomEvent) -> None:
    await app.show()
    win_state.set("Window shown")


async def on_focus_click(event: DomEvent) -> None:
    await app.focus()
    win_state.set("Window focused")


async def on_pos1(event: DomEvent) -> None:
    await app.set_bounds(100, 100, 440, 560)
    win_state.set("set_bounds(100, 100, 440, 560) applied")


async def on_pos2(event: DomEvent) -> None:
    await app.set_bounds(0, 0, 560, 720)
    win_state.set("set_bounds(0, 0, 560, 720) applied")


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


# Page-level lifecycle hooks drive the Window tab status line.
async def on_page_focus() -> None:
    win_state.set("Window focused")


async def on_page_blur() -> None:
    win_state.set("Window lost focus (or hidden)")


# Window-level key events drive the Events tab's modifier lights — they
# respond wherever keys land, even while an input has focus.
page = (
    Page(gap="0px", padding="0px", max_width="100%", fill=True, radius="12px")
    .on_focus(on_page_focus)
    .on_blur(on_page_blur)
    .on_keydown(on_mod_key)
    .on_keyup(on_mod_key)
)

# In-app shortcuts fire even while an input has focus, on any tab.  The
# handler lights its dot, then dims it again after a beat.


async def shortcut_handler(dot: Div, message: str) -> None:
    set_dot(dot, True)
    shortcut_message.set(message)
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

# ── tab: overlays ────────────────────────────────────────────────

# Dialog: a fixed full-page scrim + centered panel.  Mounted at the
# PAGE ROOT — a transform / backdrop-filter ancestor (like an animated
# panel's rise-in animation) would hijack `position: fixed` in WebKit.
# Closes via scrim / Escape / click-away; the action buttons run their
# callbacks and close by default.
dialog = Dialog(
    title="Confirm",
    content=VStack(Text("Try the scrim, Escape, click-away, or the buttons below.")),
    width="380px",
    actions=[
        DialogAction("Confirm", variant="danger", on_click=lambda d: setattr(dialog_status, "text", "Confirm clicked")),
        DialogAction("Cancel", variant="ghost"),
        DialogAction("Close"),
    ],
)
dialog_state = Signal("closed")
dialog_status = Text("", role="secondary")
dialog_status.bind_text(dialog_state)
dialog_open_btn = Button("Open dialog")


async def on_dialog_open(_event: DomEvent) -> None:
    dialog.open = True


dialog_open_btn.on_click(on_dialog_open)
dialog.on_open(lambda _dialog: dialog_state.set("open"))
dialog.on_close(lambda _dialog: dialog_state.set("closed"))

# Tooltip: anchor-relative bubble, placement offsets, hover delay.
tip_top = Tooltip("Tooltip on top", anchor=Button("Hover (top)"), placement="top", delay=1)
tip_bottom = Tooltip("Tooltip below", anchor=Button("Hover (bottom)"), placement="bottom", delay=1)

# Dropdown: themed popup under a trigger (Select's pattern).
theme_choice = Signal("")
theme_dd = Dropdown("Theme", items=[("dark", "Dark"), ("light", "Light"), ("deep-blue", "Deep Blue")], width="160px")
theme_dd.bind_value(theme_choice)
dd_echo = Text("", role="secondary")
dd_echo.bind_text(theme_choice, fmt=lambda value: f"Dropdown: {value}")

# Menu: fixed at the cursor — right-click the button.  Also mounted at
# the page root so no ancestor transform can hijack `position: fixed`.
ctx_menu = Menu(("rename", "Rename"), ("duplicate", "Duplicate"), ("delete", "Delete"))
menu_echo = Text("", role="secondary")
menu_value = Signal("")
menu_echo.bind_text(menu_value, fmt=lambda value: f"Menu: {value}")
menu_btn = Button("Right-click me", variant="ghost")


async def on_menu_contextmenu(event: DomEvent) -> None:
    ctx_menu.open_at(event.x or 0, event.y or 0)


async def on_menu_change(event: DomEvent) -> None:
    menu_value.set(f"{event.value}")


menu_btn.on_contextmenu(on_menu_contextmenu)
ctx_menu.on_change(on_menu_change)

# ── PromptDialog: a single-field text prompt ──────────────────────────

prompt = PromptDialog(
    "What's your name?",
    title="Identify",
    placeholder="Ada Lovelace…",
    value="Ada",
)
prompt_state = Signal("closed")
prompt_status = Text("", role="secondary")
prompt_status.bind_text(prompt_state)
prompt_open_btn = Button("Ask a name")


async def on_prompt_open(_event: DomEvent) -> None:
    prompt.open = True


prompt_open_btn.on_click(on_prompt_open)
prompt.on_open(lambda _dialog: prompt_state.set("open"))
prompt.on_close(lambda _dialog: prompt_state.set("closed"))


def on_prompt_submit(value: str) -> None:
    prompt_state.set(f"submitted: {value!r}")


prompt.on_submit(on_prompt_submit)

overlays_panel = Section(
    "Overlays",
    "Four positioned layers — all CSS-anchored, zero measurement. "
    "Dialog dims the whole page with a themed scrim and centers a "
    "panel with configurable action buttons (scrim / Escape / "
    "click-away close); Tooltip wraps its anchor with placement "
    "offsets and a hover delay; Dropdown reuses the popup pattern "
    "(outsideclick close, full keyboard nav); Menu is fixed at the "
    "cursor via open_at() — right-click the button.",
    """dialog = Dialog(
    title="Confirm", content=Text("..."), width="380px",
    actions=[DialogAction("Confirm", on_click=fn), DialogAction("Cancel", variant="ghost")],  # click → close
)
dialog.open = True                        # or read the property
dialog.on_close(lambda d: print("closed"))

ask = PromptDialog("Your name?", value="Ada", placeholder="Type…")
ask.open = True                           # show it
ask.on_submit(lambda v: print(f"got {v}"))  # confirm / Enter

tip = Tooltip("hint", anchor=Button("Hover"), placement="top", delay=0.4)

dd = Dropdown("Theme", items=[("dark", "Dark"), ("light", "Light")])
dd.on_change(lambda e: print(e.value))    # selected value

menu = Menu(("rename", "Rename"), ("delete", "Delete"))
btn.on_contextmenu(lambda e: menu.open_at(e.x, e.y))  # cursor position
menu.on_change(lambda e: print(e.value))""",
    HStack(Text("Dialog", weight="600"), Spacer(), dialog_open_btn, gap="8px"),
    dialog_status,
    Separator(),
    HStack(Text("PromptDialog", weight="600"), Spacer(), prompt_open_btn, gap="8px"),
    prompt_status,
    Separator(),
    HStack(tip_top, tip_bottom, gap="12px"),
    Separator(),
    HStack(Text("Dropdown", weight="600"), Spacer(), theme_dd, gap="8px"),
    dd_echo,
    Separator(),
    menu_btn,
    menu_echo,
)

page.add(dialog, ctx_menu, prompt)

# ── Content components: Card / Avatar / Badge / Image ────────────────

_IMAGE_SRC = "https://harcic.is-a.dev/resource/head.webp"

# Image: themed frame around an <img>. src is an already-built URL — pass
# it file_url(path), data_url(path), or an https URL.
img_demo = Image(_IMAGE_SRC, alt="Neony icon", width=96, height=96, radius="12px")
img_round = Image(_IMAGE_SRC, alt="round", width=64, height=64, radius="50%")

# Avatar: image, initial, or placeholder; optional corner badge.
av_image = Avatar(_IMAGE_SRC, name="Neony", size="56px")
av_letter = Avatar(name="Ada Lovelace", size="56px")
av_unknown = Avatar(size="56px")
av_badge = Avatar(_IMAGE_SRC, name="Inbox", size="56px", badge=Badge(3, position="top-right", variant="accent"))

# Badge: inline pill or corner count. Counts clamp at 99+, zero hides.
badge_inline = HStack(
    Badge("New", variant="accent"),
    Badge("12", variant="danger"),
    Badge("verified", variant="success"),
    Badge("plain"),
    Badge(dot=True),
    gap="8px",
    align="center",
)
badge_count = HStack(
    Badge(5),
    Badge(150),  # → "99+"
    Badge(0),  # hidden by default
    Badge(0, show_zero=True),
    gap="10px",
    align="center",
)

# Card: titled panel with actions and a footer; clickable surfaces fire
# on_click (the badge above overlays an Avatar the same way).
card_echo = Text("", role="secondary")
plain_card = Card(
    Text("The body holds any children — text, components, or raw nodes."),
    title="Plain card",
    subtitle="A solid surface with a soft shadow",
    actions=[Button("Edit")],
    footer=[Button("Cancel"), Button("OK")],
    clickable=True,
)
plain_card.on_click(lambda _event: setattr(card_echo, "text", "Card clicked."))


glass_card = Card(
    Text("Frosted glass tinted by role — the accent glow follows the theme."),
    title="Glass card",
    subtitle="role='accent'",
    glass=True,
    role="accent",
)

content_panel = Section(
    "Content",
    "Display components — Image, Avatar, Badge, and Card. Pure presentation; "
    "they reuse the theme tokens so they redraw on theme switch.",
    """img  = Image(src, width=96, height=96, radius="12px")  # src is any URL
av   = Avatar(src, name="Ada", size="56px")
av_b = Avatar(src, name="Inbox", badge=Badge(3, position="top-right"))
bdg  = Badge("New", variant="accent")          # or Badge(150) → "99+"
dot  = Badge(dot=True)                          # status dot
card = Card(Text("body"), title="T", subtitle="s",
            actions=[Button("Edit")], footer=[Button("OK")], clickable=True)
glass= Card(Text("body"), title="T", glass=True, role="accent")""",
    Heading("Image", level=4),
    HStack(img_demo, img_round, gap="16px", align="center"),
    Separator(),
    Heading("Avatar", level=4),
    HStack(av_image, av_letter, av_unknown, av_badge, gap="16px", align="center"),
    Separator(),
    Heading("Badge", level=4),
    Text("Inline pills:", role="secondary"),
    badge_inline,
    Text("Counts (150 → 99+, 0 hidden unless show_zero):", role="secondary"),
    badge_count,
    Separator(),
    Heading("Card", level=4),
    plain_card,
    glass_card,
    card_echo,
)

# ── home: shown until a leaf is selected ─────────────────────────

home_panel = VStack(
    Heading("Welcome", level=3),
    Text(
        "This gallery is organized as a tree: pick a category on the "
        "left, expand it, and select a component to see its docs and "
        "live demos here. Every section pairs a demo with the Python "
        "snippet that produced it, so the gallery doubles as a reference.",
        role="secondary",
    ),
    gap="12px",
)

# ── tree: categories → component leaves ─────────────────────────

gallery_tree = Tree(width="220px").children(
    TreeNode("Home", key="home", icon=Icon.glyph("🏠")).panel(home_panel),
    TreeNode("Buttons", key="buttons", shortcut="Ctrl+1").panel(buttons_panel),
    TreeNode("Inputs & Forms", key="inputs-forms", expanded=True).children(
        TreeNode("Inputs", key="inputs", shortcut="Ctrl+2").panel(inputs_panel),
        TreeNode("Checks", key="checks", shortcut="Ctrl+3").panel(checks_panel),
        TreeNode("Forms", key="forms", shortcut="Ctrl+4").panel(forms_panel),
    ),
    TreeNode("Layout & Type", key="layout-type").children(
        TreeNode("Layout", key="layout").panel(layout_panel),
        TreeNode("Type", key="type").panel(typography_panel),
    ),
    TreeNode("Glass & Content", key="glass-content").children(
        TreeNode("Glass", key="glass").panel(glass_panel),
        TreeNode("Content", key="content").panel(content_panel),
        TreeNode("Icon", key="icon").panel(icon_panel),
    ),
    TreeNode("Interaction & Events", key="interaction").children(
        TreeNode("Events", key="events").panel(events_panel),
        TreeNode("Drop", key="drop").panel(drop_panel),
        TreeNode("Clipboard", key="clipboard").panel(clipboard_panel),
        TreeNode("Shortcuts", key="shortcuts").panel(shortcuts_panel),
        TreeNode("Overlays", key="overlays").panel(overlays_panel),
    ),
    TreeNode("System & Advanced", key="system").children(
        TreeNode("Animations", key="animations").panel(animations_panel),
        TreeNode("Reactive", key="reactive").panel(reactive_panel),
        TreeNode("Sidebar", key="sidebar").panel(sidebar_panel),
        TreeNode("Window", key="window").panel(window_panel),
    ),
)
gallery_tree.selected_key = "home"

# ── assemble: transparent TitleBar over a solid content stage ─────

titlebar = TitleBar("Neony — Component Gallery", icon=Icon.image(_ICON_URL))

# The content stage uses the plain theme background — only the titlebar
# above it stays transparent, so the desktop shows through the chrome
# while the docs/text get a solid, readable backdrop.  Must be a flex
# column: a bare block Div ignores flex-grow, so its height = content
# height and the tree pushes the whole page open (no bounded stage, no
# internal tree scroll).
content = Div(
    styles=Styles(
        display="flex",
        flex_direction="column",
        flex_grow="1",
        min_height="0",
        overflow="auto",
        background_color=Color(var="--color-bg"),
    ),
    # grow=1: the header + tree column must be a flex item with the
    # tree's allocated height (the tree self-bounds via flex-grow +
    # min-height:0, but an auto-height parent gives it nothing to grow
    # into — without grow=1 the tree pushes the stage open).
    container=[VStack(header, gallery_tree, gap="16px", padding="24px", grow=1).build()],
)

# grow=1 makes the chrome stack fill the window; the content stage then
# grows to fill the space below the titlebar.
page.add(VStack(titlebar, content, gap="0px", grow=1))


def main() -> None:
    app.run(page)


if __name__ == "__main__":
    main()
