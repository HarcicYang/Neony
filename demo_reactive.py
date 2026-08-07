#!/usr/bin/env python3
"""Reactive Neony demo — signals and event handlers working together.

Signals with declarative bindings keep simple state and presentation
synchronized. Named ``on_*`` handlers remain the right tool for event
context, batch updates, asynchronous work, and other multi-step behavior.
Computed values derive state, Effects handle side effects, and the binding
family keeps widgets synchronized.

Usage:
    python demo_reactive.py
"""

from neony.application import Page, launch
from neony.application.elements import Button, Checkbox, Component, Input, Tabs, Text, VStack
from neony.dom import Color, Computed, Div, DomEvent, Signal, Styles, effect

# ── tab 1: counter — the label is bound to the signal ─────────────

count = Signal(0)
counter_value = Text("0", size="48px", weight="bold")
counter_value.bind_text(count)

counter_btn = Button("+").on_click(lambda _event: count.update(lambda current: current + 1))
counter_panel = VStack(counter_value, counter_btn, gap="16px", align="center")

# ── tab 2: inputs — two-way value bindings + declarative echoes ───

name_input = Input(placeholder="Your name…")
email_input = Input(placeholder="Email", type="email")
name = Signal("")
email = Signal("")
name_input.bind_value(name)
email_input.bind_value(email)

name_echo = Text("", role="secondary")
name_echo.bind_text(name, fmt=lambda value: f"Hello, {value}!" if value else "")
email_echo = Text("", role="secondary")
email_echo.bind_text(email, fmt=lambda value: f"Email: {value}" if value else "")

inputs_panel = VStack(name_input, name_echo, email_input, email_echo, gap="12px")

# ── tab 3: checkboxes — Computed count + derived select-all state ─

FOODS = ["Pizza", "Tacos", "Ramen"]
food_flags = [Signal(False) for _ in FOODS]
food_checks = [Checkbox(name).bind_value(flag) for name, flag in zip(FOODS, food_flags, strict=True)]
selected = Computed(lambda: sum(flag() for flag in food_flags))
all_selected = Computed(lambda: bool(FOODS) and selected() == len(FOODS))

check_all = Checkbox("Select all")
check_all.bind_value(all_selected)


def on_check_all(event: DomEvent) -> None:
    for flag in food_flags:
        flag.set(bool(event.value))


check_all.on_change(on_check_all)

check_status = Text("", role="secondary")
check_status.bind_text(selected, fmt=lambda count: f"{count} of {len(FOODS)} selected")
checks_panel = VStack(check_all, *food_checks, check_status, gap="10px")

# ── tab 4: derived — Computed values + bind_style ─────────────────

first_name = Signal("")
last_name = Signal("")
first_input = Input(placeholder="First name").bind_value(first_name)
last_input = Input(placeholder="Last name").bind_value(last_name)

full_name = Computed(lambda: f"{first_name().strip()} {last_name().strip()}".strip())
full_echo = Text("", role="secondary")
full_echo.bind_text(full_name, fmt=lambda value: f"Computed full name: {value}" if value else "Type both names…")


class HeatBar(Component):
    """Demo-local signal-driven heat bar; it is not part of the library."""

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


heat = Signal(30)
heat_bar = HeatBar(heat)
heat_label = Text("", role="secondary")
heat_label.bind_text(heat, fmt=lambda number: f"heat: {number}%")
heat_plus = Button("+").on_click(lambda _event: heat.update(lambda number: max(0, min(100, number + 10))))
heat_minus = Button("-", variant="ghost").on_click(
    lambda _event: heat.update(lambda number: max(0, min(100, number - 10)))
)

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
level_log = Signal(f"Effect fired — level = {level()}")
level_text = Div(
    styles=Styles(
        font_family=_MONO,
        font_size="13px",
        color=Color(var="--color-text-secondary"),
    )
)
level_text.bind_text(level_log)

effect_slot = {"eff": None}
running = Signal(True)
effect_state = Text("", role="secondary", size="12px")
effect_state.bind_text(
    running,
    fmt=lambda active: "effect: running" if active else "effect: disposed — level changes no longer sync",
)


def level_sync() -> None:
    # An Effect re-runs this body whenever a signal it read changes.
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
level_plus = Button("Level +5").on_click(lambda _event: level.update(lambda number: max(0, min(100, number + 5))))
level_minus = Button("Level -5", variant="ghost").on_click(
    lambda _event: level.update(lambda number: max(0, min(100, number - 5)))
)

# bind_visible and bind_value share the same Signal.
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

tabs = Tabs(
    ("Counter", counter_panel),
    ("Inputs", inputs_panel),
    ("Checks", checks_panel),
    ("Derived", derived_panel),
    ("Effects", effects_panel),
)
page = Page(gap="16px", max_width="480px").add(tabs)


def main() -> None:
    launch(page, title="Neony — Reactive v2", width=480, height=560, devtools=True)


if __name__ == "__main__":
    main()
