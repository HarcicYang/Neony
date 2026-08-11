"""Buttons section."""

from __future__ import annotations

from neony.application.elements import Button, Separator, Text
from neony.dom import Color, Signal, Styles

from ..core import Section
from ..i18n import tr, tr_now

primary_btn = Button(tr.buttons.primary)
ghost_btn = Button(tr.buttons.ghost, variant="ghost")
danger_btn = Button(tr.buttons.danger, variant="danger")
disabled_btn = Button(tr.buttons.disabled, disabled=True)

# Signal-driven counter: the click handler only bumps the signal; the
# label follows via bind_text — the reactive way to hold UI state.
clicks = Signal(0)
clicks_btn = Button(tr.buttons.click_me)
clicks_btn.on_click(lambda _e: clicks.update(lambda n: n + 1))
clicks_text = Text(tr_now(tr.buttons.clicks_fmt).format(n=0), role="secondary")
clicks_text.bind_text(clicks, fmt=lambda n: tr.buttons.clicks_fmt.format(n=n).get())

# reset_styles demo: custom green button, hover feedback still works
custom_btn = Button(tr.buttons.custom).reset_styles(
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
    tr.buttons.section_title,
    tr.buttons.section_blurb,
    """Button("Primary Action")
Button("Ghost Button", variant="ghost")
Button("Delete", variant="danger")
Button("Disabled", disabled=True)
Button("Custom").reset_styles(
    Styles(background_color=Color(hex="#2fa89a"), ...))

clicks = Signal(0)
btn.on_click(lambda _e: clicks.update(lambda n: n + 1))
label.bind_text(clicks, fmt=lambda n: f"{n} clicks")""",
    primary_btn,
    ghost_btn,
    danger_btn,
    disabled_btn,
    custom_btn,
    Separator(),
    clicks_btn,
    clicks_text,
)

PANELS = {"buttons": buttons_panel}
