"""Dual-mode theme with semantic colour tokens.

Tokens are exposed to CSS as custom properties (``--color-*``) on
``:root``. Components reference them through ``Color(var=...)`` so a
theme switch re-injects the ``:root`` block and the browser redraws
every ``var(--color-*)`` — no DOM diff required.

Glass tokens (``surface_glass`` etc.) power the opt-in frosted look:
semi-transparent surfaces that let a background image show through
``backdrop-filter`` blur. They are per-theme — a light theme gets a
white translucent surface, dark themes get a dark one — so the glass
always stays in family with the palette.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

_DEEP_BLUE = {
    "bg": "#1a1a2e",
    "surface": "#252540",
    "surface_raised": "#2e2e4a",
    "text_primary": "#ffffff",
    "text_secondary": "#8080a0",
    "accent": "#4a90d9",
    "accent_dim": "#3a7bc8",
    "danger": "#ff6b6b",
    "success": "#4ecdc4",
    "border": "rgba(255, 255, 255, 0.06)",
    "shadow": "0 8px 32px rgba(0, 0, 0, 0.12)",
    "bg_overlay": "rgba(26, 26, 46, 0.7)",
    # --- glass (per-theme, tinted with the surface colour) ---
    # Deep-blue keeps a distinctly blue tint so it reads apart from
    # dark's neutral charcoal glass.
    "surface_glass": "rgba(54, 54, 92, 0.92)",
    "surface_raised_glass": "rgba(64, 64, 104, 0.92)",
    "border_glass": "rgba(255, 255, 255, 0.08)",
    "accent_glass": "rgba(74, 144, 217, 0.25)",
    "danger_glass": "rgba(255, 107, 107, 0.25)",
    "success_glass": "rgba(78, 205, 196, 0.25)",
    "surface_glass_bg": "rgba(34, 34, 74, 0.60)",
    "surface_panel_glass_bg": "rgba(34, 34, 74, 0.85)",
    "accent_glass_bg": "rgba(74, 144, 217, 0.60)",
    "danger_glass_bg": "rgba(255, 107, 107, 0.60)",
}

_DARK = {
    "bg": "#0d0d12",
    "surface": "#1a1a24",
    "surface_raised": "#242436",
    "text_primary": "#e8e8ed",
    "text_secondary": "#707088",
    "accent": "#6c8cff",
    "accent_dim": "#5570cc",
    "danger": "#ff6b6b",
    "success": "#4ecdc4",
    "border": "rgba(255, 255, 255, 0.06)",
    "shadow": "0 8px 32px rgba(0, 0, 0, 0.25)",
    "bg_overlay": "rgba(13, 13, 18, 0.7)",
    # --- glass (per-theme, tinted with the surface colour) ---
    # Neutral charcoal — deliberately low blue/purple so it reads as
    # "glass", distinct from deep-blue's tinted glass.
    "surface_glass": "rgba(52, 52, 56, 0.92)",
    "surface_raised_glass": "rgba(60, 60, 64, 0.92)",
    "border_glass": "rgba(255, 255, 255, 0.08)",
    "accent_glass": "rgba(108, 140, 255, 0.25)",
    "danger_glass": "rgba(255, 107, 107, 0.25)",
    "success_glass": "rgba(78, 205, 196, 0.25)",
    "surface_glass_bg": "rgba(40, 40, 44, 0.60)",
    "surface_panel_glass_bg": "rgba(40, 40, 44, 0.85)",
    "accent_glass_bg": "rgba(74, 144, 217, 0.60)",
    "danger_glass_bg": "rgba(255, 107, 107, 0.60)",
}

_LIGHT = {
    "bg": "#f4f5f7",
    "surface": "#ffffff",
    "surface_raised": "#fafafa",
    "text_primary": "#1a1a2e",
    "text_secondary": "#5a5a72",
    "accent": "#3a7bc8",
    "accent_dim": "#2e6bb0",
    "danger": "#d9534f",
    "success": "#2fa89a",
    "border": "rgba(0, 0, 0, 0.08)",
    "shadow": "0 8px 32px rgba(0, 0, 0, 0.08)",
    "bg_overlay": "rgba(244, 245, 247, 0.7)",
    # --- glass (per-theme, tinted with the surface colour) ---
    "surface_glass": "rgba(255, 255, 255, 0.88)",
    "surface_raised_glass": "rgba(255, 255, 255, 0.88)",
    "border_glass": "rgba(0, 0, 0, 0.12)",
    "accent_glass": "rgba(58, 123, 200, 0.2)",
    "danger_glass": "rgba(217, 83, 79, 0.2)",
    "success_glass": "rgba(47, 168, 154, 0.2)",
    "surface_glass_bg": "rgba(255, 255, 255, 0.60)",
    "surface_panel_glass_bg": "rgba(255, 255, 255, 0.85)",
    "accent_glass_bg": "rgba(58, 123, 200, 0.60)",
    "danger_glass_bg": "rgba(217, 83, 79, 0.60)",
}


class Theme(BaseModel):
    """Semantic colour palette for one display mode.

    Only ``mode`` and token fields are stored; :meth:`to_css` renders
    the ``:root`` custom-property block used by the injected stylesheet.
    """

    mode: Literal["light", "dark", "deep-blue"] = "dark"

    # --- semantic tokens (hex strings / rgba) ---
    bg: str = Field(default=_DARK["bg"])
    surface: str = Field(default=_DARK["surface"])
    surface_raised: str = Field(default=_DARK["surface_raised"])
    text_primary: str = Field(default=_DARK["text_primary"])
    text_secondary: str = Field(default=_DARK["text_secondary"])
    accent: str = Field(default=_DARK["accent"])
    accent_dim: str = Field(default=_DARK["accent_dim"])
    danger: str = Field(default=_DARK["danger"])
    success: str = Field(default=_DARK["success"])
    border: str = Field(default=_DARK["border"])
    shadow: str = Field(default=_DARK["shadow"])

    # --- background overlay (theme colour at ~70% for dimming) ---
    bg_overlay: str = Field(default=_DARK["bg_overlay"])

    # --- glass tokens (opt-in frosted look, per-theme) ---
    surface_glass: str = Field(default=_DARK["surface_glass"])
    surface_raised_glass: str = Field(default=_DARK["surface_raised_glass"])
    border_glass: str = Field(default=_DARK["border_glass"])
    accent_glass: str = Field(default=_DARK["accent_glass"])
    danger_glass: str = Field(default=_DARK["danger_glass"])
    success_glass: str = Field(default=_DARK["success_glass"])
    surface_glass_bg: str = Field(default=_DARK["surface_glass_bg"])
    surface_panel_glass_bg: str = Field(default=_DARK["surface_panel_glass_bg"])
    accent_glass_bg: str = Field(default=_DARK["accent_glass_bg"])
    danger_glass_bg: str = Field(default=_DARK["danger_glass_bg"])

    @staticmethod
    def glass_border(role: str = "neutral") -> str:
        """Highlight border colour matching a semantic role.

        Returns a CSS variable reference (``var(--color-accent-glass)``
        etc.) so the tint follows the active theme automatically.
        """
        if role in ("accent", "danger", "success"):
            return f"var(--color-{role}-glass)"
        return "var(--color-border-glass)"

    def to_css(self) -> str:
        """Generate the ``:root { --color-*: ...; }`` stylesheet block."""
        tokens: list[str] = []
        for name in type(self).model_fields:
            if name == "mode":
                continue
            tokens.append(f"--color-{name.replace('_', '-')}: {getattr(self, name)};")
        return ":root { " + " ".join(tokens) + " }"

    def to_style_element(self) -> str:
        """Wrap :meth:`to_css` in a ``<style>`` tag for inline injection."""
        return f"<style>{self.to_css()}</style>"

    def set_mode(self, mode: Literal["light", "dark", "deep-blue"]) -> None:
        """Switch to *mode* and load its palette."""
        palette = {"light": _LIGHT, "dark": _DARK, "deep-blue": _DEEP_BLUE}[mode]
        self.mode = mode
        for name, value in palette.items():
            setattr(self, name, value)

    def toggle(self) -> None:
        """Cycle through the available modes."""
        order = ("dark", "light", "deep-blue")
        self.set_mode(order[(order.index(self.mode) + 1) % len(order)])


DARK = Theme(mode="dark", **_DARK)
LIGHT = Theme(mode="light", **_LIGHT)
DEEP_BLUE = Theme(mode="deep-blue", **_DEEP_BLUE)
