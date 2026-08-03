#!/usr/bin/env python3
"""Reactive Neony demo — component library showcase.

Built entirely from components — no raw Div/Span:
  - Page: top-level flex column + theme background
  - Tabs: Counter / Inputs / Checks panels
  - Button, Input, Checkbox, Text
  - app.state for shared state, auto-render on every handler
"""

from neony.application import Page, launch
from neony.application.elements import Button, Checkbox, Input, Tabs, Text, VStack
from neony.dom import DomEvent

app_state = {"count": 0}

# ── tab 1: counter ───────────────────────────────────────────────

counter_value = Text("0", size="48px", weight="bold")
counter_btn = Button("+")


async def on_counter_click(event: DomEvent) -> None:
    app_state["count"] += 1
    counter_value.text = str(app_state["count"])


counter_btn.on_click(on_counter_click)
counter_panel = VStack(counter_value, counter_btn, gap="16px", align="center")

# ── tab 2: inputs ────────────────────────────────────────────────

name_input = Input(placeholder="Your name…")
name_echo = Text("", role="secondary")

email_input = Input(placeholder="Email", type="email")
email_echo = Text("", role="secondary")


async def on_name_input(event: DomEvent) -> None:
    name_echo.text = f"Hello, {event.value}!" if event.value else ""


async def on_email_input(event: DomEvent) -> None:
    email_echo.text = f"Email: {event.value}" if event.value else ""


name_input.on_input(on_name_input)
email_input.on_input(on_email_input)
inputs_panel = VStack(name_input, name_echo, email_input, email_echo, gap="12px")

# ── tab 3: checkboxes ────────────────────────────────────────────

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
checks_panel = VStack(check_all, *food_checks, check_status, gap="10px")

# ── assemble ─────────────────────────────────────────────────────

tabs = Tabs()
tabs.add("Counter", counter_panel)
tabs.add("Inputs", inputs_panel)
tabs.add("Checks", checks_panel)

page = Page(gap="16px", max_width="480px")
page.add(tabs)


def main() -> None:
    launch(page, title="Neony — Components", width=480, height=560, devtools=True)


if __name__ == "__main__":
    main()
