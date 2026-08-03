#!/usr/bin/env python3
"""Reactive Neony demo — multi-tab app with stateful widgets.

Built with the fluent API:
  - ``NeonApplication`` wraps App/Window/Bridge/auto-render
  - handlers bind directly to elements via ``.on_click()`` / ``.on_input()``
  - app-level state lives in ``app.state``
  - the DOM tree is mutated in place; Neony sends minimal patches
"""

from neony.application import Config, NeonApplication, WebViewConfig, WindowConfig
from neony.dom import Color, Div, DomEvent, Input, Label, Span, Styles, Textarea

# ── colours ──────────────────────────────────────────────────────

BG = Color(hex="#1a1a2e")
SURFACE = Color(hex="#252540")
ACTIVE = Color(hex="#4a90d9")
MUTED = Color(hex="#8888aa")
WHITE = Color(name="white")
GREEN = Color(hex="#4ecdc4")
PINK = Color(hex="#ff6b6b")

# ── styles ───────────────────────────────────────────────────────

page = Styles(
    display="flex",
    flex_direction="column",
    align_items="center",
    min_height="100vh",
    background_color=BG,
    font_family="system-ui, sans-serif",
    color=WHITE,
)
tab_bar = Styles(display="flex", gap="4px", padding="16px 16px 0 16px")
tab_off = Styles(
    padding="10px 24px",
    border_radius="8px 8px 0 0",
    font_size="14px",
    font_weight="500",
    cursor="pointer",
    background_color=SURFACE,
    color=MUTED,
)
tab_on = tab_off.model_copy(update={"background_color": ACTIVE, "color": WHITE})
panel_off = Styles(
    display="none",
    flex_direction="column",
    align_items="center",
    gap="20px",
    padding="40px 24px",
    background_color=SURFACE,
    border_radius="0 8px 8px 8px",
    width="360px",
)
panel_on = panel_off.model_copy(update={"display": "flex"})
field = Styles(
    width="100%",
    padding="10px 14px",
    border_radius="8px",
    border="1px solid #444",
    background_color=BG,
    color=WHITE,
    font_size="15px",
    outline="none",
)
echo = Styles(color=GREEN, font_size="13px", padding="4px 0")
check_row = Styles(display="flex", align_items="center", gap="10px", font_size="15px", cursor="pointer")
muted = Styles(color=MUTED, font_size="13px")
big = Styles(
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

app = NeonApplication(
    Config(
        window=WindowConfig(title="Neony — Multi-Tab Demo", width=480, height=640),
        webview=WebViewConfig(devtools=True),
    )
)
FOOD = ["pizza", "tacos", "ramen"]
app.state.count = 0

# ── elements ─────────────────────────────────────────────────────
#
# Keys are auto-generated (uuid4) — no manual key strings needed.
# Handlers bind to element references; the bridge resolves identity
# through each element's own key at registration time.

counter = Div(styles=big, container=["0"])
tab_counter = Div(styles=tab_on, container=["Counter"])
tab_inputs = Div(styles=tab_off, container=["Inputs"])
tab_checks = Div(styles=tab_off, container=["Checks"])
panel_counter = Div(styles=panel_on, container=[counter])
text_input = Input(type="text", placeholder="Your text here…", styles=field)
text_echo = Span(styles=echo)
text_area = Textarea(placeholder="Write anything…", styles=field)
textarea_echo = Span(styles=echo)
panel_inputs = Div(styles=panel_off, container=[text_input, text_echo, text_area, textarea_echo])
check_all = Input(type="checkbox")
food_checks: list[Input] = []
food_labels: list[Label] = []
for name in FOOD:
    cb = Input(type="checkbox")
    food_checks.append(cb)
    food_labels.append(Label(styles=check_row, container=[cb, Span(container=[name.capitalize()])]))
check_status = Span(styles=Styles(color=PINK, font_size="14px", font_weight="600"))
panel_checks = Div(
    styles=panel_off,
    container=[
        Label(styles=check_row, container=[check_all, Span(container=["Select / deselect all"])]),
        *food_labels,
        check_status,
    ],
)
tree = Div(
    styles=page,
    container=[
        Div(styles=tab_bar, container=[tab_counter, tab_inputs, tab_checks]),
        panel_counter,
        panel_inputs,
        panel_checks,
    ],
)


# ── helpers ──────────────────────────────────────────────────────

TABS = [(tab_counter, panel_counter), (tab_inputs, panel_inputs), (tab_checks, panel_checks)]


def switch_tab(idx: int) -> None:
    for i, (tab, panel) in enumerate(TABS):
        tab.styles = tab_on if i == idx else tab_off
        panel.styles = panel_on if i == idx else panel_off


def check_value(cb: Input) -> bool:
    return bool(cb.checked)


def set_checked(cb: Input, checked: bool) -> None:
    cb.checked = checked


def update_checks() -> None:
    n = sum(check_value(cb) for cb in food_checks)
    set_checked(check_all, n == len(FOOD))
    text = f"{n} of {len(FOOD)} selected" if n else "0 of 3 selected"
    if n:
        names = [name.capitalize() for name, cb in zip(FOOD, food_checks, strict=True) if check_value(cb)]
        text += f"  ({', '.join(names)})"
    check_status.container = [text]


# ── handlers ─────────────────────────────────────────────────────


def make_tab_handler(idx: int):
    async def handler(event: DomEvent) -> None:
        switch_tab(idx)

    return handler


for i in range(3):
    TABS[i][0].on_click(make_tab_handler(i))


async def on_counter_click(event: DomEvent) -> None:
    app.state.count += 1
    counter.container = [str(app.state.count)]
    hue = (200 + app.state.count * 15) % 360
    counter.styles.background_color = Color(hex=f"hsl({hue}, 70%, 50%)")


counter.on_click(on_counter_click)


async def on_text_input(event: DomEvent) -> None:
    text_input.value = event.value
    text_echo.container = [f"You typed: {event.value}"] if event.value else [""]


text_input.on_input(on_text_input)


async def on_textarea_input(event: DomEvent) -> None:
    text_area.value = event.value
    textarea_echo.container = [f"Length: {len(event.value)} chars"] if event.value else [""]


text_area.on_input(on_textarea_input)


async def on_check_all(event: DomEvent) -> None:
    for cb in food_checks:
        set_checked(cb, bool(event.value))
    update_checks()


check_all.on_change(on_check_all)


def make_food_handler(cb: Input):
    """Handler factory — each checkbox closes over its own element."""

    async def handler(event: DomEvent) -> None:
        set_checked(cb, bool(event.value))
        update_checks()

    return handler


for cb in food_checks:
    cb.on_change(make_food_handler(cb))

# ── run ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    app.run(tree)
