"""Glass, Content and Window Icon sections."""

from __future__ import annotations

from neony.application.elements import (
    Avatar,
    Badge,
    Button,
    Card,
    Checkbox,
    GlassPanel,
    Heading,
    HStack,
    Image,
    Input,
    Separator,
    Text,
    VStack,
)
from neony.dom import Signal

from ..core import _BACKGROUND_URL, Section

# ── tab: glass ───────────────────────────────────────────────────

glass_input = Input(placeholder="Glass input…", glass=True)
glass_input_echo = Text("", role="secondary")
glass_value = Signal("")
glass_input.bind_value(glass_value)
glass_input_echo.bind_text(glass_value, fmt=lambda value: f"Typed: {value}" if value else "")

# One frosted stage carries the background image; the glass components
# inside it (glass=True, no background of their own) blur it through
# their translucent, theme-tinted surfaces.  role="accent" adds a
# persistent colour-matched glow around the panel.
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
    role="accent",
)

# Role glows: a semantic role tints both the hairline border and the
# persistent outer glow — success below, danger right.
success_stage = GlassPanel(
    Text("Success — role glows follow the theme", role="success"),
    gap="8px",
    padding="12px 16px",
    role="success",
)
danger_stage = GlassPanel(
    Text("Danger — destructive emphasis", role="danger"),
    gap="8px",
    padding="12px 16px",
    role="danger",
)

# Per-corner radii: each corner gets its own rounding — useful when a
# panel joins rounded chrome (e.g. the titlebar / sidebar seams).
corners_stage = GlassPanel(
    Text("Per-corner radii — 24px / 4px / 24px / 4px", role="secondary"),
    gap="8px",
    padding="12px 16px",
    border_top_left_radius="24px",
    border_top_right_radius="4px",
    border_bottom_left_radius="24px",
    border_bottom_right_radius="4px",
)

glass_panel = Section(
    "Frosted Glass",
    "GlassPanel blurs the background image; components with glass=True "
    "keep their theme colours while gaining the frosted surface. A "
    "semantic role tints the panel's border AND its outer glow; "
    "per-corner radii join chrome at any angle.",
    """GlassPanel(Heading("Frosted"), background=url, role="accent")
GlassPanel(Text("…"), role="success")
GlassPanel(..., border_top_left_radius="24px", ...)
Button("Primary", glass=True)
Checkbox("Glass", glass=True)""",
    glass_demo,
    success_stage,
    danger_stage,
    corners_stage,
)

# ── tab: icon ─────────────────────────────────────────────────────

# Frameless windows have no OS window chrome, so the icon can't be set
# via WindowConfig — it's painted inline in the TitleBar instead.  The
# window header above shows the live result.
icon_panel = Section(
    "Window Icon",
    "Frameless windows show the icon inline in the TitleBar; decorated "
    "windows hand it to the OS window chrome via WindowConfig.icon — "
    "both take the same URL or file path. file_url() / data_url() turn "
    "local files into URL strings for icons, backgrounds and images.",
    """# Frameless — inline in the TitleBar (this window):
TitleBar("My App", icon=Icon.image("https://harcic.is-a.dev/resource/favicon.svg"))

# Decorated — the OS window chrome shows it:
launch(page, title="My App", icon="icon.png")
# or: Config(window=WindowConfig(title="My App", icon="icon.png"))

# Runtime swap (either mode):
await app.set_icon("icon.png")

# Local resources:
from neony.application import file_url, data_url
GlassPanel(background=file_url("bg.png"))
TitleBar(icon=Icon.image(data_url("logo.svg")))""",
    VStack(
        Text("Live: the favicon in the titlebar above uses TitleBar(icon=...).", role="secondary"),
        Text(
            "For decorated windows the taskbar / titlebar icon comes from "
            "WindowConfig.icon; TitleBar(icon=...) only affects frameless chrome.",
            role="secondary",
        ),
        gap="8px",
    ),
)

# ── Content components: Card / Avatar / Badge / Image ────────────────

_IMAGE_SRC = "https://harcic.is-a.dev/resource/head.webp"

# Image: themed frame around an <img>. src is an already-built URL — pass
# it file_url(path), data_url(path), or an https URL.
img_demo = Image(_IMAGE_SRC, alt="Neony icon", width=96, height=96, radius="12px")
img_round = Image(_IMAGE_SRC, alt="round", width=64, height=64, radius="50%")

# Avatar: image, initial, or placeholder; optional corner badge.
av_image = Avatar(_IMAGE_SRC, name="Neony", size="56px")
av_letter = Avatar(name="Ada Lovelace", size="56px")
av_unknown = Avatar(size="56px")
av_badge = Avatar(_IMAGE_SRC, name="Inbox", size="56px", badge=Badge(3, position="top-right", variant="accent"))

# Badge: inline pill or corner count. Counts clamp at 99+, zero hides.
badge_inline = HStack(
    Badge("New", variant="accent"),
    Badge("12", variant="danger"),
    Badge("verified", variant="success"),
    Badge("plain"),
    Badge(dot=True),
    gap="8px",
    align="center",
)
badge_count = HStack(
    Badge(5),
    Badge(150),  # → "99+"
    Badge(0),  # hidden by default
    Badge(0, show_zero=True),
    gap="10px",
    align="center",
)

# Card: titled panel with actions and a footer; clickable surfaces fire
# on_click (the badge above overlays an Avatar the same way).
card_echo = Text("", role="secondary")
plain_card = Card(
    Text("The body holds any children — text, components, or raw nodes."),
    title="Plain card",
    subtitle="A solid surface with a soft shadow",
    actions=[Button("Edit")],
    footer=[Button("Cancel"), Button("OK")],
    clickable=True,
)
plain_card.on_click(lambda _event: setattr(card_echo, "text", "Card clicked."))


glass_card = Card(
    Text("Frosted glass tinted by role — the accent glow follows the theme."),
    title="Glass card",
    subtitle="role='accent'",
    glass=True,
    role="accent",
)

content_panel = Section(
    "Content",
    "Display components — Image, Avatar, Badge, and Card. Pure presentation; "
    "they reuse the theme tokens so they redraw on theme switch.",
    """img  = Image(src, width=96, height=96, radius="12px")  # src is any URL
av   = Avatar(src, name="Ada", size="56px")
av_b = Avatar(src, name="Inbox", badge=Badge(3, position="top-right"))
bdg  = Badge("New", variant="accent")          # or Badge(150) → "99+"
dot  = Badge(dot=True)                          # status dot
card = Card(Text("body"), title="T", subtitle="s",
            actions=[Button("Edit")], footer=[Button("OK")], clickable=True)
glass= Card(Text("body"), title="T", glass=True, role="accent")""",
    Heading("Image", level=4),
    HStack(img_demo, img_round, gap="16px", align="center"),
    Separator(),
    Heading("Avatar", level=4),
    HStack(av_image, av_letter, av_unknown, av_badge, gap="16px", align="center"),
    Separator(),
    Heading("Badge", level=4),
    Text("Inline pills:", role="secondary"),
    badge_inline,
    Text("Counts (150 → 99+, 0 hidden unless show_zero):", role="secondary"),
    badge_count,
    Separator(),
    Heading("Card", level=4),
    plain_card,
    glass_card,
    card_echo,
)

PANELS = {"glass": glass_panel, "content": content_panel, "icon": icon_panel}
