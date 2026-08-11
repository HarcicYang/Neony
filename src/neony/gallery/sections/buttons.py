"""Buttons section."""

from __future__ import annotations

from neony.application.elements import Button, Separator, Text
from neony.dom import Color, Signal, Styles

from ..core import Section

primary_btn = Button("Primary Action")
ghost_btn = Button("Ghost Button", variant="ghost")
danger_btn = Button("Delete", variant="danger")
disabled_btn = Button("Disabled", disabled=True)

# Signal-driven counter: the click handler only bumps the signal; the
# label follows via bind_text — the reactive way to hold UI state.
clicks = Signal(0)
clicks_btn = Button("Click me")
clicks_btn.on_click(lambda _e: clicks.update(lambda n: n + 1))
clicks_text = Text("0 clicks", role="secondary")
clicks_text.bind_text(clicks, fmt=lambda n: f"{n} clicks")

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
    "Three variants (primary, ghost, danger) with hover / press feedback "
    "and colour-matched glows — hover lifts with a halo in the variant's "
    "own colour, focus draws a tinted ring. reset_styles() replaces the "
    "base look while keeping the feedback. The counter holds its state "
    "in a Signal — the click only bumps it, bind_text redraws the label.",
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
