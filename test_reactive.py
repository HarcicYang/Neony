#!/usr/bin/env python3
"""Reactive Neony demo — multi-tab app with stateful widgets.

Tabs:
  Counter  — click-to-increment with animated colour
  Inputs   — text field + textarea with live echo
  Checks   — checkboxes with select-all and status display

All tab panels live in the DOM tree permanently; switching tabs only
toggles ``display`` styles so that widget state (input values, checkbox
checkedness, etc.) is preserved without any extra effort.
"""

import asyncio

from lumiview import App, Bridge, Window

from neony.dom import Color, Div, Input, Label, Span, Styles, Textarea
from neony.dom.bridge import Neony

app = App(name="ReactiveTabs")
neony_app = Neony()

# ── Colour palette ───────────────────────────────────────────────

BG = Color(hex="#1a1a2e")
SURFACE = Color(hex="#252540")
ACTIVE = Color(hex="#4a90d9")
MUTED = Color(hex="#8888aa")
WHITE = Color(name="white")
ACCENT_GREEN = Color(hex="#4ecdc4")
ACCENT_PINK = Color(hex="#ff6b6b")

# ── Shared styles ────────────────────────────────────────────────

page_styles = Styles(
    display="flex",
    flex_direction="column",
    align_items="center",
    min_height="100vh",
    background_color=BG,
    font_family="system-ui, sans-serif",
    color=WHITE,
)

tab_bar_styles = Styles(
    display="flex",
    gap="4px",
    padding="16px 16px 0 16px",
)

tab_base = Styles(
    padding="10px 24px",
    border_radius="8px 8px 0 0",
    font_size="14px",
    font_weight="500",
    cursor="pointer",
    background_color=SURFACE,
    color=MUTED,
)

tab_active = Styles(
    padding="10px 24px",
    border_radius="8px 8px 0 0",
    font_size="14px",
    font_weight="500",
    cursor="pointer",
    background_color=ACTIVE,
    color=WHITE,
)

panel_base = Styles(
    display="none",
    flex_direction="column",
    align_items="center",
    gap="20px",
    padding="40px 24px",
    background_color=SURFACE,
    border_radius="0 8px 8px 8px",
    width="360px",
)

panel_active = Styles(
    display="flex",
    flex_direction="column",
    align_items="center",
    gap="20px",
    padding="40px 24px",
    background_color=SURFACE,
    border_radius="0 8px 8px 8px",
    width="360px",
)

# ── Tab 1: Counter ───────────────────────────────────────────────

counter_styles = Styles(
    color=WHITE,
    background_color=ACTIVE,
    font_size="56px",
    font_weight="bold",
    width="100px",
    height="100px",
    display="flex",
    justify_content="center",
    align_items="center",
    border_radius="16px",
    cursor="pointer",
)

hint_styles = Styles(color=MUTED, font_size="13px")

# ── Tab 2: Inputs ────────────────────────────────────────────────

input_field_styles = Styles(
    width="100%",
    padding="10px 14px",
    border_radius="8px",
    border="1px solid #444",
    background_color=BG,
    color=WHITE,
    font_size="15px",
    outline="none",
)

echo_styles = Styles(
    color=ACCENT_GREEN,
    font_size="13px",
    padding="4px 0",
)

textarea_styles = Styles(
    width="100%",
    padding="10px 14px",
    border_radius="8px",
    border="1px solid #444",
    background_color=BG,
    color=WHITE,
    font_size="14px",
    outline="none",
    min_height="80px",
    resize="none",
)

# ── Tab 3: Checks ─────────────────────────────────────────────────

check_label_styles = Styles(
    display="flex",
    align_items="center",
    gap="10px",
    font_size="15px",
    cursor="pointer",
)

status_styles = Styles(
    color=ACCENT_PINK,
    font_size="14px",
    font_weight="600",
)

summary_section_styles = Styles(
    display="flex",
    flex_direction="column",
    gap="8px",
    padding="24px",
    margin_top="24px",
    background_color=SURFACE,
    border_radius="8px",
    width="360px",
)

summary_title_styles = Styles(
    color=ACCENT_GREEN,
    font_size="13px",
    font_weight="600",
    margin_bottom="4px",
)

summary_row_styles = Styles(
    color=MUTED,
    font_size="12px",
    font_family="monospace",
)

# ── Build the tree ───────────────────────────────────────────────

tree = Div(
    key="page",
    styles=page_styles,
    container=[
        # -- tab bar --
        Div(
            key="tab_bar",
            styles=tab_bar_styles,
            container=[
                Div(key="tab_counter", styles=tab_active, container=["Counter"]),
                Div(key="tab_inputs", styles=tab_base, container=["Inputs"]),
                Div(key="tab_checks", styles=tab_base, container=["Checks"]),
            ],
        ),
        # -- panel 1: Counter --
        Div(
            key="panel_counter",
            styles=panel_active,
            container=[
                Div(key="counter", styles=counter_styles, container=["0"]),
                Span(key="counter_hint", styles=hint_styles, container=["Click the number above"]),
            ],
        ),
        # -- panel 2: Inputs --
        Div(
            key="panel_inputs",
            styles=panel_base,
            container=[
                Span(key="input_label", styles=Styles(font_size="14px", color=MUTED), container=["Type something:"]),
                Input(
                    key="text_input",
                    args={"type": "text", "placeholder": "Your text here…"},
                    styles=input_field_styles,
                ),
                Span(key="text_echo", styles=echo_styles, container=[""]),
                Span(key="textarea_label", styles=Styles(font_size="14px", color=MUTED), container=["More text:"]),
                Textarea(key="text_area", args={"placeholder": "Write anything…"}, styles=textarea_styles),
                Span(key="textarea_echo", styles=echo_styles, container=[""]),
            ],
        ),
        # -- panel 3: Checks --
        Div(
            key="panel_checks",
            styles=panel_base,
            container=[
                Label(
                    key="lbl_select_all",
                    styles=check_label_styles,
                    container=[
                        Input(key="check_all", args={"type": "checkbox"}),
                        Span(key="lbl_all_text", container=["Select / deselect all"]),
                    ],
                ),
                Label(
                    key="lbl_pizza",
                    styles=check_label_styles,
                    container=[
                        Input(key="check_pizza", args={"type": "checkbox"}),
                        Span(container=["Pizza"]),
                    ],
                ),
                Label(
                    key="lbl_tacos",
                    styles=check_label_styles,
                    container=[
                        Input(key="check_tacos", args={"type": "checkbox"}),
                        Span(container=["Tacos"]),
                    ],
                ),
                Label(
                    key="lbl_ramen",
                    styles=check_label_styles,
                    container=[
                        Input(key="check_ramen", args={"type": "checkbox"}),
                        Span(container=["Ramen"]),
                    ],
                ),
                Span(key="check_status", styles=status_styles, container=["0 of 3 selected"]),
            ],
        ),
        # -- summary bar (always visible, shows all Python-side state) --
        Div(
            key="summary_section",
            styles=summary_section_styles,
            container=[
                Span(key="summary_title", styles=summary_title_styles, container=["📋 Python State"]),
                Span(key="summary_counter", styles=summary_row_styles, container=["counter  = 0"]),
                Span(key="summary_text", styles=summary_row_styles, container=['text    = ""']),
                Span(key="summary_textarea", styles=summary_row_styles, container=["textarea = 0 chars"]),
                Span(key="summary_checks", styles=summary_row_styles, container=["checks  = 0 / 3"]),
            ],
        ),
    ],
)

# ── Helpers ──────────────────────────────────────────────────────

TAB_KEYS = ["tab_counter", "tab_inputs", "tab_checks"]
PANEL_KEYS = ["panel_counter", "panel_inputs", "panel_checks"]
CHECK_KEYS = ["check_pizza", "check_tacos", "check_ramen"]

# Indexed lookup into the tab-bar / content area
tab_bar = tree.container[0]
assert isinstance(tab_bar, Div)
panels = tree.container[1:4]  # panel_counter, panel_inputs, panel_checks

current_tab = 0
count = 0


def _tab_el(i: int) -> Div:
    el = tab_bar.container[i]
    assert isinstance(el, Div)
    return el


def _panel_el(i: int) -> Div:
    el = panels[i]
    assert isinstance(el, Div)
    return el


def _counter_el() -> Div:
    panel = _panel_el(0)
    el = panel.container[0]
    assert isinstance(el, Div)
    return el


def _echo_el(idx: int) -> Span:
    """Text echo (index 2) or textarea echo (index 5) inside panel_inputs."""
    panel = _panel_el(1)
    el = panel.container[idx]
    assert isinstance(el, Span)
    return el


def _check_el(key: str) -> Input:
    panel = _panel_el(2)
    for item in panel.container:
        if isinstance(item, Label):
            for child in item.container:
                if isinstance(child, Input) and child.key == key:
                    return child
    raise KeyError(key)


def _check_status_el() -> Span:
    panel = _panel_el(2)
    el = panel.container[-1]
    assert isinstance(el, Span)
    return el


def _input_el(key: str) -> Input | Textarea:
    """Find an Input or Textarea inside panel_inputs by key."""
    panel = _panel_el(1)
    for item in panel.container:
        if isinstance(item, (Input, Textarea)) and item.key == key:
            return item
    raise KeyError(key)


# summary is tree.container[4]
_summary = tree.container[4]
assert isinstance(_summary, Div)


def _summary_row(idx: int) -> Span:
    el = _summary.container[idx]
    assert isinstance(el, Span)
    return el


def _update_summary() -> None:
    """Sync the always-visible summary bar with current Python state."""
    text_val = _input_el("text_input").args.get("value", "")
    ta_val = _input_el("text_area").args.get("value", "")
    checked = [ck for ck in CHECK_KEYS if _check_el(ck).args.get("checked")]
    _summary_row(1).container = [f"counter  = {count}"]
    _summary_row(2).container = [f"text    = {text_val!r}"]
    _summary_row(3).container = [f"textarea = {len(ta_val)} chars"]
    _summary_row(4).container = [f"checks  = {len(checked)} / {len(CHECK_KEYS)}"]


def switch_tab(index: int) -> None:
    """Update tab button and panel visibility styles."""
    for i in range(3):
        _tab_el(i).styles = tab_active if i == index else tab_base
        p = _panel_el(i)
        assert isinstance(p, Div)
        p.styles = panel_active if i == index else panel_base


# ── Event handlers ───────────────────────────────────────────────


@neony_app.on("click", key="tab_counter")
async def on_tab_counter(key, event_type, value):
    global current_tab
    current_tab = 0
    switch_tab(0)
    await neony_app.render(tree)


@neony_app.on("click", key="tab_inputs")
async def on_tab_inputs(key, event_type, value):
    global current_tab
    current_tab = 1
    switch_tab(1)
    await neony_app.render(tree)


@neony_app.on("click", key="tab_checks")
async def on_tab_checks(key, event_type, value):
    global current_tab
    current_tab = 2
    switch_tab(2)
    await neony_app.render(tree)


@neony_app.on("click", key="counter")
async def on_counter_click(key, event_type, value):
    global count
    count += 1
    counter_el = _counter_el()
    counter_el.container = [str(count)]
    hue = (200 + count * 15) % 360
    counter_el.styles.background_color = Color(hex=f"hsl({hue}, 70%, 50%)")
    _update_summary()
    await neony_app.render(tree)
    print(f"[counter] {count}")


@neony_app.on("input", key="text_input")
async def on_text_input(key, event_type, value):
    # Sync DOM state → Python tree
    _input_el("text_input").args["value"] = value
    echo = _echo_el(2)  # text_echo span
    echo.container = [f"You typed: {value}"] if value else [""]
    _update_summary()
    await neony_app.render(tree)
    print(f"[input ] text = {value!r}")


@neony_app.on("input", key="text_area")
async def on_textarea_input(key, event_type, value):
    _input_el("text_area").args["value"] = value
    echo = _echo_el(5)  # textarea_echo span
    echo.container = [f"Length: {len(value)} chars"] if value else [""]
    _update_summary()
    await neony_app.render(tree)
    print(f"[input ] textarea length = {len(value)}")


@neony_app.on("change", key="check_all")
async def on_check_all(key, event_type, value):
    """Select-all checkbox toggles every food checkbox."""
    checked = bool(value)
    # Sync all checkboxes (including select-all itself)
    _check_el("check_all").args["checked"] = checked
    for ck in CHECK_KEYS:
        _check_el(ck).args["checked"] = checked
    _update_check_status()
    _update_summary()
    await neony_app.render(tree)
    print(f"[checks] select-all = {checked}")


@neony_app.on("change", key="check_pizza")
@neony_app.on("change", key="check_tacos")
@neony_app.on("change", key="check_ramen")
async def on_food_check(key, event_type, value):
    # Sync Python state with the live DOM
    _check_el(key).args["checked"] = bool(value)
    # Keep the select-all checkbox in sync
    checked_count = sum(1 for ck in CHECK_KEYS if _check_el(ck).args.get("checked"))
    sync_all = checked_count == 3
    _check_el("check_all").args["checked"] = sync_all
    _update_check_status()
    _update_summary()
    await neony_app.render(tree)
    names = [ck.replace("check_", "").capitalize() for ck in CHECK_KEYS if _check_el(ck).args.get("checked")]
    print(f"[checks] {checked_count}/{len(CHECK_KEYS)} selected: {names}  sync_all={sync_all}")


def _update_check_status() -> None:
    checked = [ck for ck in CHECK_KEYS if _check_el(ck).args.get("checked")]
    n = len(checked)
    total = len(CHECK_KEYS)
    names = [ck.replace("check_", "").capitalize() for ck in checked]
    text = f"{n} of {total} selected" if n > 0 else "0 of 3 selected"
    if n > 0:
        text += f"  ({', '.join(names)})"
    _check_status_el().container = [text]


# ── Bootstrap ────────────────────────────────────────────────────


async def main():
    _win = await Window.create(
        title="Neony — Multi-Tab Demo",
        html="<html><body><div id='neony-root'></div></body></html>",
        width=480,
        height=560,
        devtools=True,
        bridge=Bridge(includes=[neony_app]),
    )
    await asyncio.sleep(0.5)
    await neony_app.render(tree)
    print("[neony] multi-tab demo ready — try switching tabs")


app.run(main)
