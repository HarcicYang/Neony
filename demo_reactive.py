#!/usr/bin/env python3
"""Reactive Neony demo — the signal-based API.

State flows through Signals with declarative bindings instead of
hand-written refresh calls.  Compare:

    # v1 — manual sync (every mutation needs a DOM write)
    app_state["count"] += 1
    counter_value.text = str(app_state["count"])

    # v2 — declarative: the label follows the signal
    counter_value.bind_text(count)

Showcases Signal, Computed (derived values), Effect (side effects with
dispose), and the full binding family: bind_text, bind_style (width AND
colour), bind_visible.

Usage:
    python demo_reactive.py
"""

from neony.application import Page, launch
from neony.application.elements import Button, Checkbox, Input, Tabs, Text, VStack
from neony.dom import Color, Computed, Div, DomEvent, Signal, Styles, effect

# ── tab 1: counter — the label is BOUND to the signal ─────────────

count = Signal(0)
counter_value = Text("0", size="48px", weight="bold")
counter_value.bind_text(count)  # no manual refresh needed

counter_btn = Button("+")


async def on_counter_click(event: DomEvent) -> None:
    count.update(lambda c: c + 1)


counter_btn.on_click(on_counter_click)
counter_panel = VStack(counter_value, counter_btn, gap="16px", align="center")

# ── tab 2: inputs — computed echo instead of event handlers ───────

name_input = Input(placeholder="Your name…")
email_input = Input(placeholder="Email", type="email")

name = Signal("")
email = Signal("")

name_echo = Text("", role="secondary")
name_echo.bind_text(name, fmt=lambda v: f"Hello, {v}!" if v else "")

email_echo = Text("", role="secondary")
email_echo.bind_text(email, fmt=lambda v: f"Email: {v}" if v else "")


async def on_name_input(event: DomEvent) -> None:
    name.set(event.value)


async def on_email_input(event: DomEvent) -> None:
    email.set(event.value)


name_input.on_input(on_name_input)
email_input.on_input(on_email_input)
inputs_panel = VStack(name_input, name_echo, email_input, email_echo, gap="12px")

# ── tab 3: checkboxes — bound count + derived "select all" state ──

FOODS = ["Pizza", "Tacos", "Ramen"]
food_checks = [Checkbox(name) for name in FOODS]
check_all = Checkbox("Select all")
selected = Signal(0)
check_status = Text("0 of 3 selected", role="secondary")
check_status.bind_text(
    selected,
    fmt=lambda n: f"{n} of {len(FOODS)} selected",
)


def refresh_selected() -> None:
    selected.set(sum(1 for cb in food_checks if cb.checked))
    check_all.checked = selected() == len(FOODS)


for cb in food_checks:
    cb.on_change(lambda _e: refresh_selected())


async def on_check_all(event: DomEvent) -> None:
    for cb in food_checks:
        cb.checked = bool(event.value)
    refresh_selected()


check_all.on_change(on_check_all)
checks_panel = VStack(check_all, *food_checks, check_status, gap="10px")

# ── tab 4: derived — Computed values + bind_style ─────────────────

first_name = Signal("")
last_name = Signal("")
first_input = Input(placeholder="First name")
last_input = Input(placeholder="Last name")

# A Computed caches its result and recomputes only when a dependency
# changes; bind_text accepts it like any other source.
full_name = Computed(lambda: f"{first_name().strip()} {last_name().strip()}".strip())
full_echo = Text("", role="secondary")
full_echo.bind_text(full_name, fmt=lambda v: f"Computed full name: {v}" if v else "Type both names…")


async def on_first_input(event: DomEvent) -> None:
    first_name.set(event.value)


async def on_last_input(event: DomEvent) -> None:
    last_name.set(event.value)


first_input.on_input(on_first_input)
last_input.on_input(on_last_input)

# bind_style: width AND colour follow one signal (the fmt receives the
# current value and returns the style value — a string or a Color).
heat = Signal(30)
heat_bar = Div(
    styles=Styles(
        height="14px",
        border_radius="7px",
        background_color=Color(var="--color-border"),
        transition="all 0.15s ease",
    )
)
heat_bar.bind_style(heat, "width", fmt=lambda n: f"{max(0, min(100, n))}%")
heat_bar.bind_style(
    heat,
    "background_color",
    fmt=lambda n: Color(
        rgb=(
            int(40 + 2.1 * max(0, min(100, n))),
            int(190 - 1.3 * max(0, min(100, n))),
            120,
        )
    ),
)
heat_label = Text("heat: 30%", role="secondary")
heat_label.bind_text(heat, fmt=lambda n: f"heat: {n}%")

heat_plus = Button("+")
heat_minus = Button("-", variant="ghost")
heat_plus.on_click(lambda _e: heat.update(lambda n: max(0, min(100, n + 10))))
heat_minus.on_click(lambda _e: heat.update(lambda n: max(0, min(100, n - 10))))

derived_panel = VStack(
    Text("Computed — derived values that recompute on dependency change", role="secondary"),
    first_input,
    last_input,
    full_echo,
    Text("bind_style — width and colour follow the signal", role="secondary"),
    heat_plus,
    heat_minus,
    heat_bar,
    heat_label,
    gap="12px",
)

# ── tab 5: effects — side effects with dispose ────────────────────

level = Signal(50)
_MONO = "ui-monospace, Menlo, Consolas, monospace"
level_text = Div(
    styles=Styles(
        font_family=_MONO,
        font_size="13px",
        color=Color(var="--color-text-secondary"),
    )
)

effect_slot = {"eff": None}


def level_sync() -> None:
    # An Effect re-runs this body whenever a signal it read changes.
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

level_plus = Button("Level +5")
level_minus = Button("Level -5", variant="ghost")
level_plus.on_click(lambda _e: level.update(lambda n: max(0, min(100, n + 5))))
level_minus.on_click(lambda _e: level.update(lambda n: max(0, min(100, n - 5))))

# bind_visible: the checkbox drives display via a Signal.
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

effects_panel = VStack(
    Text("Effect — runs immediately, re-runs on dependency change, dispose() stops it", role="secondary"),
    level_plus,
    level_minus,
    effect_btn,
    level_text,
    effect_state,
    Text("bind_visible — display follows a Signal", role="secondary"),
    secret_check,
    secret_block,
    gap="12px",
)

# ── assemble ─────────────────────────────────────────────────────

tabs = Tabs()
tabs.add("Counter", counter_panel)
tabs.add("Inputs", inputs_panel)
tabs.add("Checks", checks_panel)
tabs.add("Derived", derived_panel)
tabs.add("Effects", effects_panel)

page = Page(gap="16px", max_width="480px")
page.add(tabs)


def main() -> None:
    launch(page, title="Neony — Reactive v2", width=480, height=560, devtools=True)


if __name__ == "__main__":
    main()
