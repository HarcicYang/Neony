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

Usage:
    python demo_gallery.py
"""

import asyncio
import os
import sys

from neony.application import Config, NeonApplication, Page, WebViewConfig, WindowConfig
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
    Image,
    Input,
    Menu,
    Progress,
    PromptDialog,
    Radio,
    RadioGroup,
    Select,
    Separator,
    Sidebar,
    SidebarItem,
    Slider,
    Spacer,
    Switch,
    Tabs,
    Text,
    TitleBar,
    Tooltip,
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
    "value; echoing it back is the standard pattern (password/email use "
    "the same event with their own readouts).",
    """inp = Input(placeholder="Your name…")
async def on_text_input(event: DomEvent) -> None:
    text_echo.text = f"Hello, {event.value}!"
inp.on_input(on_text_input)

pwd = Input(placeholder="Password", type="password")   # email / number …
pwd.on_input(lambda e: print(len(e.value)))""",
    text_input,
    text_echo,
    password_input,
    password_echo,
    email_input,
    email_echo,
)

# ── tab: checks ──────────────────────────────────────────────────

# The signals are the single source of truth: each checkbox is bound
# two-way, "Select all" is a Computed driven by an effect, and the
# status line is a bound text — no manual refresh calls.
FOODS = ["Pizza", "Tacos", "Ramen"]
food_flags = {name: Signal(False) for name in FOODS}
food_checks = [Checkbox(name) for name in FOODS]
for cb, name in zip(food_checks, FOODS, strict=True):
    cb.bind_value(food_flags[name])

all_selected = Computed(lambda: all(food_flags[name]() for name in FOODS))
check_all = Checkbox("Select all")
check_all_effect = effect(lambda: setattr(check_all, "checked", all_selected()))
check_status = Text("0 of 3 selected", role="secondary")
check_status.bind_text(Computed(lambda: f"{sum(1 for name in FOODS if food_flags[name]())} of {len(FOODS)} selected"))


async def on_check_all(event: DomEvent) -> None:
    for name in FOODS:
        food_flags[name].set(bool(event.value))


check_all.on_change(on_check_all)

checks_panel = Section(
    "Checkboxes",
    "Custom-styled toggles with a change event. Signals are the single "
    "source of truth: each food checkbox is bound two-way via "
    'bind_value, "Select all" is a Computed driven by an effect, and '
    "the status line is a bound text — nothing refreshes by hand.",
    """flag = Signal(False)
cb = Checkbox("Pizza")
cb.bind_value(flag)      # two-way: toggling writes the signal

all_selected = Computed(lambda: all(f[name]() for name in FOODS))
effect(lambda: setattr(check_all, "checked", all_selected()))
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
meal_echo = Text("Picked: pizza", role="secondary")


async def on_meal_change(event: DomEvent) -> None:
    meal_echo.text = f"Picked: {event.value}"


meal_group.on_change(on_meal_change)

wifi_switch = Switch("Wi-Fi")
wifi_status = Text("Off", role="secondary")


async def on_wifi_change(event: DomEvent) -> None:
    wifi_status.text = "On" if event.value else "Off"


wifi_switch.on_change(on_wifi_change)

size_select = Select(
    "Size",
    options=[("s", "Small"), ("m", "Medium"), ("l", "Large")],
    placeholder="Pick a size…",
    value="m",
)
size_echo = Text("Selected: m", role="secondary")


async def on_size_change(event: DomEvent) -> None:
    size_echo.text = f"Selected: {event.value}"


size_select.on_change(on_size_change)

tag_combobox = ComboBox("Tag", options=["work", "personal", "travel"], placeholder="Type or pick…")
tag_echo = Text("", role="secondary")


async def on_tag_input(event: DomEvent) -> None:
    tag_echo.text = f"Tag: {event.value}" if event.value else ""


async def on_tag_change(event: DomEvent) -> None:
    # auto-complete (Tab/Enter/PageUp/PageDown) fires change, not input —
    # the readout must follow picks too
    tag_echo.text = f"Tag: {event.value}" if event.value else ""


tag_combobox.on_input(on_tag_input)
tag_combobox.on_change(on_tag_change)

# One signal drives three widgets: the slider writes it (bind_value is
# two-way), the readout and the progress bar follow (bind_text /
# bind_value write-only).  No manual refresh anywhere.
volume = Signal(40)
volume_slider = Slider("Volume (stepped)", min=0, max=100, step=5, value=40)
volume_slider.bind_value(volume)
volume_readout = Mono()
volume_readout.bind_text(volume, fmt=lambda v: f"{v:.0f}%")
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

load_bar = Progress(value=35, label="Downloading…")
scan_bar = Progress(label="Scanning…", indeterminate=True)
advance_btn = Button("+15%", variant="ghost")


async def on_advance(_event: DomEvent) -> None:
    load_bar.value = min(100.0, load_bar.value + 15)


advance_btn.on_click(on_advance)

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
# labels) bubbles to this bubble_events Div.  The DomEvent carries the
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
tracker.bubble_events = True


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
wheel_zone.bubble_events = True


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

# Pointer move: live tracking.  movement_x/y are the delta since the
# last pointermove — no manual position bookkeeping needed — and
# pointer_type tells mouse / pen / touch apart.  Pointermove rides the
# deferred render path, so the readout coalesces to one render per
# frame instead of one per event.
pointer_readout = Mono()
pointer_readout.container = ["—"]
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
    pointer_readout.container = [
        f"({event.x:.0f}, {event.y:.0f})   "
        f"movement ({event.movement_x:+.0f}, {event.movement_y:+.0f})   "
        f"{event.pointer_type or '?'}"
    ]


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
spin_state = Text("running", size="12px", role="secondary")


async def on_spin_toggle(event: DomEvent) -> None:
    anim = spinner.styles.animation
    paused = isinstance(anim, Animation) and anim.play_state == "paused"
    if isinstance(anim, Animation):
        spinner.styles.animation = anim.model_copy(update={"play_state": "paused" if not paused else "running"})
    spin_state.text = "paused" if not paused else "running"


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
drop_zone.bubble_events = True


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


async def on_read_click(event: DomEvent) -> None:
    try:
        text = await app.clipboard_read()
    except Exception as exc:  # permission denied / no gesture
        clip_line.container = [f"read failed: {exc}"]
        clip_log_line(f"clipboard_read() failed: {exc}")
        return
    clip_line.container = [f"read: {text!r}"]


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

# batch(): two signals changed together flush ONE effect run.
batch_a = Signal(0)
batch_b = Signal(0)
batch_runs = {"n": 0}
batch_count = Mono()


def batch_sync() -> None:
    batch_runs["n"] += 1
    batch_count.container = [f"effect runs: {batch_runs['n']}  (a={batch_a()}, b={batch_b()})"]


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
untrack_runs = {"n": 0}
untrack_count = Mono()


def untrack_sync() -> None:
    untrack_runs["n"] += 1
    value = untrack(untrack_ignored.get)
    untrack_count.container = [
        f"effect runs: {untrack_runs['n']}  (tracked={untrack_tracked()}, "
        f"ignored={value} read via untrack — no subscription)"
    ]


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

# ── tab: overlays ────────────────────────────────────────────────

# Dialog: a fixed full-page scrim + centered panel.  Mounted at the
# PAGE ROOT — a transform / backdrop-filter ancestor (like a Tabs
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
dialog_status = Text("closed", role="secondary")
dialog_open_btn = Button("Open dialog")


async def on_dialog_open(_event: DomEvent) -> None:
    dialog.open = True


dialog_open_btn.on_click(on_dialog_open)
dialog.on_open(lambda _d: setattr(dialog_status, "text", "open"))
dialog.on_close(lambda _d: setattr(dialog_status, "text", "closed"))

# Tooltip: anchor-relative bubble, placement offsets, hover delay.
tip_top = Tooltip("Tooltip on top", anchor=Button("Hover (top)"), placement="top", delay=1)
tip_bottom = Tooltip("Tooltip below", anchor=Button("Hover (bottom)"), placement="bottom", delay=1)

# Dropdown: themed popup under a trigger (Select's pattern).
theme_dd = Dropdown("Theme", items=[("dark", "Dark"), ("light", "Light"), ("deep-blue", "Deep Blue")], width="160px")
dd_echo = Text("", role="secondary")


async def on_dd_change(event: DomEvent) -> None:
    dd_echo.text = f"Dropdown: {event.value}"


theme_dd.on_change(on_dd_change)

# Menu: fixed at the cursor — right-click the button.  Also mounted at
# the page root so no ancestor transform can hijack `position: fixed`.
ctx_menu = Menu(("rename", "Rename"), ("duplicate", "Duplicate"), ("delete", "Delete"))
menu_echo = Text("", role="secondary")
menu_btn = Button("Right-click me", variant="ghost")


async def on_menu_contextmenu(event: DomEvent) -> None:
    ctx_menu.open_at(event.x or 0, event.y or 0)


async def on_menu_change(event: DomEvent) -> None:
    menu_echo.text = f"Menu: {event.value}"


menu_btn.on_contextmenu(on_menu_contextmenu)
ctx_menu.on_change(on_menu_change)

# ── PromptDialog: a single-field text prompt ──────────────────────────

prompt = PromptDialog(
    "What's your name?",
    title="Identify",
    placeholder="Ada Lovelace…",
    value="Ada",
)
prompt_status = Text("closed", role="secondary")
prompt_open_btn = Button("Ask a name")


async def on_prompt_open(_event: DomEvent) -> None:
    prompt.open = True


prompt_open_btn.on_click(on_prompt_open)
prompt.on_open(lambda _d: setattr(prompt_status, "text", "open"))
prompt.on_close(lambda _d: setattr(prompt_status, "text", "closed"))


def on_prompt_submit(value: str) -> None:
    prompt_status.text = f"submitted: {value!r}"


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

# Fixed overlays must not live inside the Tabs panel (its rise-in
# animation transforms would hijack `position: fixed` in WebKit) —
# mount them at the page root.
page.add(dialog)
page.add(ctx_menu)
page.add(prompt)

# ── Content components: Card / Avatar / Badge / Image ────────────────

_IMAGE_SRC = "https://harcic.is-a.dev/resource/favicon.svg"

# Image: themed frame around an <img>. src is an already-built URL — pass
# it file_url(path), data_url(path), or an https URL.
img_demo = Image(_IMAGE_SRC, alt="Neony icon", width=96, height=96, radius="12px")
img_round = Image(_IMAGE_SRC, alt="round", width=64, height=64, radius="50%")

# Avatar: image, initial, or placeholder; optional corner badge.
av_image = Avatar(_IMAGE_SRC, name="Neony", size="56px")
av_letter = Avatar(name="Ada Lovelace", size="56px")
av_unknown = Avatar(size="56px")
av_badge = Avatar(_IMAGE_SRC, name="Inbox", size="56px", badge=Badge(3, position="top-right"))

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
plain_card.on_click(lambda e: _set_text(card_echo, "Card clicked."))


def _set_text(component, value):
    component.text = value


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

tabs = Tabs(glass=True)
tabs.add("Buttons", buttons_panel)
tabs.add("Inputs", inputs_panel)
tabs.add("Checks", checks_panel)
tabs.add("Forms", forms_panel)
tabs.add("Layout", layout_panel)
tabs.add("Type", typography_panel)
tabs.add("Glass", glass_panel)
tabs.add("Icon", icon_panel)
tabs.add("Events", events_panel)
tabs.add("Animations", animations_panel)
tabs.add("Drop", drop_panel)
tabs.add("Clipboard", clipboard_panel)
tabs.add("Shortcuts", shortcuts_panel)
tabs.add("Overlays", overlays_panel)
tabs.add("Reactive", reactive_panel)
tabs.add("Sidebar", sidebar_panel)
tabs.add("Window", window_panel)
tabs.add("Content", content_panel)

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
