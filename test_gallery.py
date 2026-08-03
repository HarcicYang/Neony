#!/usr/bin/env python3
"""Neony component gallery — every component with docs and code samples.

Each tab pairs a live component demo with a short description and the
Python snippet that produced it, so the gallery doubles as a reference.

Showcases: Button variants, Input types, Checkbox state, layout
primitives (HStack/Flex/Spacer), typography roles, and the frosted
glass look (GlassPanel + glass=True components).
"""

from neony.application import Config, NeonApplication, Page, WebViewConfig, WindowConfig
from neony.application.elements import (
    Button,
    Checkbox,
    Component,
    Flex,
    GlassPanel,
    Heading,
    HStack,
    Input,
    Separator,
    Spacer,
    Tabs,
    Text,
    TitleBar,
    VStack,
)
from neony.dom import Color, Div, DOMElement, DomEvent, Styles

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

_MONO = "ui-monospace, 'SF Mono', Menlo, Consolas, monospace"


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
    "Three variants (primary, ghost, danger) with hover / press feedback; "
    "disabled dims. reset_styles() replaces the base look while keeping "
    "the feedback.",
    """Button("Primary Action")
Button("Ghost Button", variant="ghost")
Button("Delete", variant="danger")
Button("Disabled", disabled=True)
Button("Custom").reset_styles(
    Styles(background_color=Color(hex="#2fa89a"), ...))""",
    primary_btn,
    ghost_btn,
    danger_btn,
    disabled_btn,
    custom_btn,
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
    "value; echoing it back is the standard pattern.",
    """inp = Input(placeholder="Your name…")
async def on_text_input(event: DomEvent) -> None:
    text_echo.text = f"Hello, {event.value}!"
inp.on_input(on_text_input)""",
    text_input,
    text_echo,
    password_input,
    password_echo,
    email_input,
    email_echo,
)

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

checks_panel = Section(
    "Checkboxes",
    "Custom-styled toggles with a change event. Setting .checked "
    "programmatically updates the view but never fires callbacks.",
    """cb = Checkbox("Pizza")
cb.checked = True  # programmatic — no callback fires
cb.on_change(lambda e: print(e.value))""",
    check_all,
    *food_checks,
    check_status,
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
    "HStack rows with Spacer pushing content; Flex gives full control, including wrapping.",
    """HStack(Text("Title"), Spacer(), Button("Edit"), gap="8px")
Flex(*items, direction="row", wrap="wrap", gap="8px")""",
    row_example,
    wrap_example,
)

# ── tab: typography ──────────────────────────────────────────────

typography_panel = Section(
    "Typography",
    "Six heading levels plus semantic text roles that follow the theme.",
    """Heading("Title", level=1)
Text("Body copy")
Text("Muted copy", role="secondary")
Text("Danger", role="danger")""",
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
)

glass_panel = Section(
    "Frosted Glass",
    "GlassPanel blurs the background image; components with glass=True "
    "keep their theme colours while gaining the frosted surface.",
    """GlassPanel(Heading("Frosted"), background=url)
Button("Primary", glass=True)
Checkbox("Glass", glass=True)""",
    glass_demo,
)

# ── assemble ─────────────────────────────────────────────────────

tabs = Tabs(glass=True)
tabs.add("Buttons", buttons_panel)
tabs.add("Inputs", inputs_panel)
tabs.add("Checks", checks_panel)
tabs.add("Layout", layout_panel)
tabs.add("Type", typography_panel)
tabs.add("Glass", glass_panel)

# ── assemble: transparent TitleBar over a solid content stage ─────

titlebar = TitleBar("Neony — Component Gallery")

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

page = Page(gap="0px", padding="0px", max_width="100%", fill=True, radius="12px")
# grow=1 makes the chrome stack fill the window; the content stage then
# grows to fill the space below the titlebar.
page.add(VStack(titlebar, content, gap="0px", align="stretch", grow=1))


def main() -> None:
    app.run(page)


if __name__ == "__main__":
    main()
