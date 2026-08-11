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
from ..i18n import tr, tr_now

# ── tab: inputs ──────────────────────────────────────────────────

text_input = Input(placeholder=tr.forms.name_placeholder)
text_echo = Text("", role="secondary")
text_value = Signal("")
text_input.bind_value(text_value)
text_echo.bind_text(text_value, fmt=lambda value: tr.forms.hello_fmt.format(value=value).get() if value else "")

password_input = Input(placeholder=tr.forms.password_placeholder, type="password")
password_echo = Text("", role="secondary")
password_value = Signal("")
password_input.bind_value(password_value)
password_echo.bind_text(
    password_value, fmt=lambda value: tr.forms.length_fmt.format(value=len(value)).get() if value else ""
)

email_input = Input(placeholder=tr.forms.email_placeholder, type="email")
email_echo = Text("", role="secondary")
email_value = Signal("")
email_input.bind_value(email_value)
email_echo.bind_text(email_value, fmt=lambda value: tr.forms.email_fmt.format(value=value).get() if value else "")

inputs_panel = Section(
    tr.forms.inputs_title,
    tr.forms.inputs_blurb,
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
# The label keys stay static English (they double as flag keys); only
# the visible labels translate.
_FOOD_LABELS = {"Pizza": tr.forms.pizza, "Tacos": tr.forms.tacos, "Ramen": tr.forms.ramen}
FOODS = ["Pizza", "Tacos", "Ramen"]
food_flags = {name: Signal(False) for name in FOODS}
food_checks = [Checkbox(_FOOD_LABELS[name]).bind_value(food_flags[name]) for name in FOODS]

all_selected = Computed(lambda: all(food_flags[name]() for name in FOODS))
check_all = Checkbox(tr.forms.select_all)
check_all.bind_value(all_selected)


def on_check_all(event: DomEvent) -> None:
    for flag in food_flags.values():
        flag.set(bool(event.value))


check_all.on_change(on_check_all)
check_status = Text("", role="secondary")
check_status.bind_text(
    Computed(
        lambda: tr.forms.selected_count_fmt.format(
            n=sum(1 for name in FOODS if food_flags[name]()),
            total=len(FOODS),
        ).get()
    )
)

checks_panel = Section(
    tr.forms.checks_title,
    tr.forms.checks_blurb,
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
    Radio(tr.forms.pizza, value="pizza"),
    Radio(tr.forms.tacos, value="tacos"),
    Radio(tr.forms.ramen, value="ramen"),
)
meal = Signal("pizza")
meal_group.bind_selected(meal)
meal_echo = Text("", role="secondary")
meal_echo.bind_text(meal, fmt=lambda value: tr.forms.picked_fmt.format(value=value).get())

wifi = Signal(False)
wifi_switch = Switch(tr.forms.wifi)
wifi_switch.bind_value(wifi)
wifi_status = Text("", role="secondary")
wifi_status.bind_text(
    wifi,
    fmt=lambda enabled: tr.forms.on.get() if enabled else tr.forms.off.get(),
)

size = Signal("m")
size_select = Select(
    tr.forms.size,
    options=[("s", tr.forms.small), ("m", tr.forms.medium), ("l", tr.forms.large)],
    placeholder=tr_now(tr.forms.pick_size_placeholder),
    value="m",
)
size_select.bind_value(size)
size_echo = Text("", role="secondary")
size_echo.bind_text(size, fmt=lambda value: tr.forms.selected_fmt.format(value=value).get())

tag = Signal("")
tag_combobox = ComboBox(tr.forms.tag, options=["work", "personal", "travel"], placeholder=tr.forms.tag_placeholder)
tag_combobox.bind_value(tag)
tag_echo = Text("", role="secondary")
tag_echo.bind_text(tag, fmt=lambda value: tr.forms.tag_fmt.format(value=value).get() if value else "")

# One signal drives three widgets: slider, readout and progress bar.
volume = Signal(40)
volume_slider = Slider(tr.forms.volume_stepped, min=0, max=100, step=5, value=40)
volume_slider.bind_value(volume)
volume_readout = Mono()
volume_readout.bind_text(volume, fmt=lambda value: f"{value:.0f}%")
volume_progress = Progress(label=tr.forms.progress_follows)
volume_progress.bind_value(volume)

# step="any" → stepless: every float is reachable, the fill follows the
# thumb instantly while dragging and glides on programmatic sets.
smooth_volume = Signal(40.0)
smooth_slider = Slider(tr.forms.volume_continuous, min=0, max=100, step="any", value=40)
smooth_slider.bind_value(smooth_volume)
smooth_readout = Mono()
smooth_readout.bind_text(smooth_volume, fmt=lambda v: f"{v:.1f}%")

# Cross-tab reactivity: this readout follows the `heat` signal that the
# Reactive tab's buttons drive — switch tabs and bump it there.
heat_share = Text("", role="secondary", size="12px")
heat_share.bind_text(heat, fmt=lambda n: tr.forms.shared_heat_fmt.format(n=n).get())

load = Signal(35)
load_bar = Progress(tr.forms.downloading, value=35)
load_bar.bind_value(load)
scan_bar = Progress(tr.forms.scanning, indeterminate=True)
advance_btn = Button(tr.forms.advance, variant="ghost").on_click(
    lambda _event: load.update(lambda value: min(100, value + 15))
)

forms_panel = Section(
    tr.forms.forms_title,
    tr.forms.forms_blurb,
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
