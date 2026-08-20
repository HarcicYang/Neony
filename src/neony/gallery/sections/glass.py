"""Glass, Content and Window Icon sections."""

from __future__ import annotations

from neony.application import icons
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
from ..i18n import tr, tr_now

# ── tab: glass ───────────────────────────────────────────────────

glass_input = Input(placeholder=tr.glass.input_placeholder, glass=True)
glass_input_echo = Text("", role="secondary")
glass_value = Signal("")
glass_input.bind_value(glass_value)
glass_input_echo.bind_text(
    glass_value,
    fmt=lambda value: tr.glass.typed_fmt.format(value=value).get() if value else "",
)

# One frosted stage carries the background image; the glass components
# inside it (glass=True, no background of their own) blur it through
# their translucent, theme-tinted surfaces.  role="accent" adds a
# persistent colour-matched glow around the panel.
glass_demo = GlassPanel(
    Heading(tr.glass.frosted_stage, level=4),
    Text(tr.glass.stage_desc, role="secondary"),
    HStack(
        Button(tr.glass.primary, glass=True),
        Button(tr.glass.ghost, variant="ghost", glass=True),
        Button(tr.glass.danger, variant="danger", glass=True),
        gap="8px",
    ),
    glass_input,
    glass_input_echo,
    Checkbox(tr.glass.glass_checkbox, glass=True),
    gap="16px",
    background=_BACKGROUND_URL,
    role="accent",
)

# Role glows: a semantic role tints both the hairline border and the
# persistent outer glow — success below, danger right.
success_stage = GlassPanel(
    Text(tr.glass.success_glow, role="success"),
    gap="8px",
    padding="12px 16px",
    role="success",
)
danger_stage = GlassPanel(
    Text(tr.glass.danger_emphasis, role="danger"),
    gap="8px",
    padding="12px 16px",
    role="danger",
)

# Per-corner radii: each corner gets its own rounding — useful when a
# panel joins rounded chrome (e.g. the titlebar / sidebar seams).
corners_stage = GlassPanel(
    Text(tr.glass.corners_desc, role="secondary"),
    gap="8px",
    padding="12px 16px",
    border_top_left_radius="24px",
    border_top_right_radius="4px",
    border_bottom_left_radius="24px",
    border_bottom_right_radius="4px",
)

glass_panel = Section(
    tr.glass.glass_title,
    tr.glass.glass_blurb,
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
    tr.glass.icon_title,
    tr.glass.icon_blurb,
    """# Built-in UI icons — imported from the stub namespace:
from neony.application import icons
Button("Save", icon=icons.check)
SidebarItem("Home", icon=icons.home)

# Explicit custom content remains available:
Icon.glyph("🍒")
TitleBar(icon=Icon.image("https://example.com/logo.svg"))

# Window / taskbar icons are separate native resources:
launch(page, title="My App", icon="icon.png")
await app.set_icon("icon.png")""",
    HStack(
        Button("Save", icon=icons.check),
        Button("Settings", icon=icons.settings, variant="ghost"),
        Button("Delete", icon=icons.delete, variant="danger"),
        gap="8px",
    ),
    VStack(
        Text(tr.glass.icon_live, role="secondary"),
        Text(tr.glass.icon_decorated, role="secondary"),
        gap="8px",
    ),
)

# ── Content components: Card / Avatar / Badge / Image ────────────────

_IMAGE_SRC = "https://harcic.is-a.dev/resource/head.webp"

# Image: themed frame around an <img>. src is an already-built URL — pass
# it file_url(path), data_url(path), or an https URL.
img_demo = Image(_IMAGE_SRC, alt=tr_now(tr.glass.image_alt), width=96, height=96, radius="12px")
img_round = Image(_IMAGE_SRC, alt=tr_now(tr.glass.image_alt_round), width=64, height=64, radius="50%")

# Avatar: image, initial, or placeholder; optional corner badge.  The
# ``name`` is a display name (people/projects) — not translated.
av_image = Avatar(_IMAGE_SRC, name="Neony", size="56px")
av_letter = Avatar(name=tr_now(tr.glass.av_ada), size="56px")
av_unknown = Avatar(size="56px")
av_badge = Avatar(_IMAGE_SRC, name="Inbox", size="56px", badge=Badge(3, position="top-right", variant="accent"))

# Badge: inline pill or corner count. Counts clamp at 99+, zero hides.
badge_inline = HStack(
    Badge(tr.glass.badge_new, variant="accent"),
    Badge("12", variant="danger"),
    Badge(tr.glass.badge_verified, variant="success"),
    Badge(tr.glass.badge_plain),
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
    Text(tr.glass.card_body),
    title=tr.glass.plain_card_title,
    subtitle=tr.glass.plain_card_subtitle,
    actions=[Button(tr.glass.edit)],
    footer=[Button(tr.common.cancel), Button(tr.common.ok)],
    clickable=True,
)
plain_card.on_click(lambda _event: setattr(card_echo, "text", tr_now(tr.glass.card_clicked)))


glass_card = Card(
    Text(tr.glass.glass_card_body),
    title=tr.glass.glass_card_title,
    subtitle=tr.glass.glass_card_subtitle,
    glass=True,
    role="accent",
)

content_panel = Section(
    tr.glass.content_title,
    tr.glass.content_blurb,
    """img  = Image(src, width=96, height=96, radius="12px")  # src is any URL
av   = Avatar(src, name="Elysia", size="56px")
av_b = Avatar(src, name="Inbox", badge=Badge(3, position="top-right"))
bdg  = Badge("New", variant="accent")          # or Badge(150) → "99+"
dot  = Badge(dot=True)                          # status dot
card = Card(Text("body"), title="T", subtitle="s",
            actions=[Button("Edit")], footer=[Button("OK")], clickable=True)
glass= Card(Text("body"), title="T", glass=True, role="accent")""",
    Heading(tr.glass.image_heading, level=4),
    HStack(img_demo, img_round, gap="16px", align="center"),
    Separator(),
    Heading(tr.glass.avatar_heading, level=4),
    HStack(av_image, av_letter, av_unknown, av_badge, gap="16px", align="center"),
    Separator(),
    Heading(tr.glass.badge_heading, level=4),
    Text(tr.glass.inline_pills, role="secondary"),
    badge_inline,
    Text(tr.glass.counts_desc, role="secondary"),
    badge_count,
    Separator(),
    Heading(tr.glass.card_heading, level=4),
    plain_card,
    glass_card,
    card_echo,
)

PANELS = {"glass": glass_panel, "content": content_panel, "icon": icon_panel}
