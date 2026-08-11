"""Inputs, Checks and Forms sections."""

from __future__ import annotations

from neony.application.elements import (
    Button,
    Checkbox,
    ComboBox,
    Input,
    Progress,
    Radio,
    RadioGroup,
    Select,
    Separator,
    Slider,
    Switch,
    Text,
)
from neony.dom import Computed, DomEvent, Signal

from ..core import Mono, Section, heat

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

PANELS = {"inputs": inputs_panel, "checks": checks_panel, "forms": forms_panel}
