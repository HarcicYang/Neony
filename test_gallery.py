#!/usr/bin/env python3
"""Neony component gallery — every component in one app.

Showcases: Page, VStack/HStack/Flex/Spacer/Separator, Heading, Text,
Button (all variants + hover/press), Input, Checkbox, Tabs, GlassPanel,
and the 3-way theme toggle (Dark / Light / Deep Blue).

The "Glass" tab sets a background image behind the UI so the frosted
surfaces (backdrop-filter) are clearly visible.
"""

from neony.application import Config, NeonApplication, Page, WebViewConfig, WindowConfig
from neony.application.elements import (
    Button,
    Checkbox,
    Flex,
    GlassPanel,
    Heading,
    HStack,
    Input,
    Separator,
    Spacer,
    Tabs,
    Text,
    VStack,
)
from neony.dom import Color, DomEvent, Styles

app = NeonApplication(
    Config(
        window=WindowConfig(title="Neony — Component Gallery", width=520, height=680),
        webview=WebViewConfig(devtools=True),
    )
)

_BACKGROUND_URL = "https://harcic.is-a.dev/resource/backgrounds/8.webp"

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
    Text("Every component, one page", role="secondary"),
    HStack(Spacer(), theme_btn, gap="8px"),
    Separator(),
    gap="12px",
)

# ── tab: buttons ─────────────────────────────────────────────────

primary_btn = Button("Primary Action")
ghost_btn = Button("Ghost Button", variant="ghost")
danger_btn = Button("Delete", variant="danger")
disabled_btn = Button("Disabled", disabled=True)

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

buttons_panel = VStack(
    primary_btn,
    ghost_btn,
    danger_btn,
    disabled_btn,
    custom_btn,
    gap="12px",
    align="stretch",
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

inputs_panel = VStack(text_input, text_echo, password_input, password_echo, email_input, email_echo, gap="10px")

# ── tab: checks ──────────────────────────────────────────────────

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

layout_panel = VStack(
    Heading("HStack + Spacer", level=4),
    row_example,
    Separator(),
    Heading("Flex (wrapping)", level=4),
    wrap_example,
    gap="12px",
)

# ── tab: typography ──────────────────────────────────────────────

typography_panel = VStack(
    Heading("Heading 1", level=1),
    Heading("Heading 2", level=2),
    Heading("Heading 3", level=3),
    Heading("Heading 4", level=4),
    Heading("Heading 5", level=5),
    Heading("Heading 6", level=6),
    Separator(),
    Text("Primary text — the default body copy."),
    Text("Secondary text — muted, less important.", role="secondary"),
    Text("Danger text — errors and destructive emphasis.", role="danger"),
    Text("Success text — confirmations.", role="success"),
    gap="8px",
)

# ── tab: glass ───────────────────────────────────────────────────

glass_input = Input(placeholder="Glass input…", glass=True)
glass_input_echo = Text("", role="secondary")


async def on_glass_input(event: DomEvent) -> None:
    glass_input_echo.text = f"Typed: {event.value}" if event.value else ""


glass_input.on_input(on_glass_input)

# One frosted stage carries the background image; the glass components
# inside it (glass=True, no background of their own) blur it through
# their translucent, theme-tinted surfaces.
glass_panel = GlassPanel(
    Heading("Frosted Glass", level=3),
    Text(
        "The stage blurs the background image; components keep their theme colours while gaining the frosted look.",
        role="secondary",
    ),
    Separator(),
    HStack(
        Button("Primary", glass=True),
        Button("Ghost", variant="ghost", glass=True),
        Button("Danger", variant="danger", glass=True),
        gap="8px",
    ),
    glass_input,
    glass_input_echo,
    Checkbox("Glass checkbox", glass=True),
    Checkbox("Select all (glass)", glass=True),
    gap="16px",
    background=_BACKGROUND_URL,
)

# ── assemble ─────────────────────────────────────────────────────

tabs = Tabs(glass=True)
tabs.add("Buttons", buttons_panel)
tabs.add("Inputs", inputs_panel)
tabs.add("Checks", checks_panel)
tabs.add("Layout", layout_panel)
tabs.add("Type", typography_panel)
tabs.add("Glass", glass_panel)

page = Page(gap="16px", max_width="720px")
page.add(header)
page.add(tabs)


def main() -> None:
    app.run(page)


if __name__ == "__main__":
    main()
