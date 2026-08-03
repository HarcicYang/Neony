"""Dual-mode theme with semantic colour tokens.

Tokens are exposed to CSS as custom properties (``--color-*``) on
``:root``. Components reference them through ``Color(var=...)`` so a
theme switch re-injects the ``:root`` block and the browser redraws
every ``var(--color-*)`` — no DOM diff required.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

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
}

_DARK = {
    "bg": "#1a1a2e",
    "surface": "#252540",
    "surface_raised": "#2e2e4a",
    "text_primary": "#ffffff",
    "text_secondary": "#8888aa",
    "accent": "#4a90d9",
    "accent_dim": "#3a7bc8",
    "danger": "#ff6b6b",
    "success": "#4ecdc4",
    "border": "rgba(255, 255, 255, 0.06)",
    "shadow": "0 8px 32px rgba(0, 0, 0, 0.12)",
}


class Theme(BaseModel):
    """Semantic colour palette for one display mode.

    Only ``mode`` and token fields are stored; :meth:`to_css` renders
    the ``:root`` custom-property block used by the injected stylesheet.
    """

    mode: Literal["light", "dark"] = "dark"

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

    def set_mode(self, mode: Literal["light", "dark"]) -> None:
        """Switch to *mode* and load its palette."""
        palette = _LIGHT if mode == "light" else _DARK
        self.mode = mode
        for name, value in palette.items():
            setattr(self, name, value)

    def toggle(self) -> None:
        """Flip between light and dark."""
        self.set_mode("light" if self.mode == "dark" else "dark")


DARK = Theme(mode="dark", **_DARK)
LIGHT = Theme(mode="light", **_LIGHT)
