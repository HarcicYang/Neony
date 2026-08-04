#!/usr/bin/env python3
"""Reactive Neony demo — the signal-based API.

The same components as test_reactive.py, but state flows through
Signals with declarative bindings instead of hand-written refresh
calls.  Compare:

    # v1 — manual sync (every mutation needs a DOM write)
    app_state["count"] += 1
    counter_value.text = str(app_state["count"])

    # v2 — declarative: the label follows the signal
    counter_value.bind_text(count)

Usage:
    python test_reactive_v2.py
"""

from neony.application import Page, launch
from neony.application.elements import Button, Checkbox, Input, Tabs, Text, VStack
from neony.dom import DomEvent, Signal

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

# ── assemble ─────────────────────────────────────────────────────

tabs = Tabs()
tabs.add("Counter", counter_panel)
tabs.add("Inputs", inputs_panel)
tabs.add("Checks", checks_panel)

page = Page(gap="16px", max_width="480px")
page.add(tabs)


def main() -> None:
    launch(page, title="Neony — Reactive v2", width=480, height=560, devtools=True)


if __name__ == "__main__":
    main()
