"""Dual-mode theme with semantic colour tokens.

Tokens are exposed to CSS as custom properties (``--color-*``) on
``:root``; components reference them via ``Color(var=...)`` so a theme
switch re-injects the block and the browser redraws — no DOM diff.
Glass tokens (``surface_glass`` etc.) are per-theme, so the frosted
look always stays in family with the palette.
"""

from __future__ import annotations

from typing import ClassVar, Literal

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
    "surface_raised": "#ebebeb",
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

    #: The display modes in :meth:`toggle` order (also the order
    #: :meth:`mode_label` derives its labels from).  ClassVar — not a
    #: model field, so it never serializes into the CSS block.
    modes: ClassVar[tuple[Literal["dark", "light", "deep-blue"], ...]] = ("dark", "light", "deep-blue")

    @staticmethod
    def mode_label(mode: str) -> str:
        """Human label describing the mode that follows *mode* in the
        toggle cycle — what a theme-toggle button promises next, e.g.
        ``Theme.mode_label("dark") == "Light mode"``.  Raises
        ``ValueError`` for unknown modes."""
        order = Theme.modes
        nxt = order[(order.index(mode) + 1) % len(order)]
        return f"{nxt.replace('-', ' ').title()} mode"

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
        """Highlight border colour for a semantic role (``var(--color-*-glass)``)."""
        if role in ("accent", "danger", "success"):
            return f"var(--color-{role}-glass)"
        return "var(--color-border-glass)"

    @staticmethod
    def focus_glow(role: str = "accent") -> str:
        """3px focus-ring halo using the role's glass token (neutral
        roles resolve to the subtle border glass)."""
        return f"0 0 0 3px {Theme.glass_border(role)}"

    @staticmethod
    def _scrollbar_css() -> str:
        """Scrollbars are hidden entirely.  ``::-webkit-scrollbar`` is
        sized to 0 / ``display:none`` so nothing renders, and Firefox
        gets ``scrollbar-width:none``.  Scrolling still works via wheel,
        touch and keyboard; only the visible bar is removed.

        Hiding (rather than styling) sidesteps WebKitGTK's native hover:
        its UA sheet grows the thumb on hover, and that growth is not
        suppressable through ``::-webkit-scrollbar-thumb:hover`` — every
        CSS property pinned to the rest value still left the thumb
        growing.  With no scrollbar drawn, there is nothing to grow.

        The custom scroll-indicator thumb (JS-built overlay appended to
        each ``data-neony-scroll`` surface) takes the bar's place — it
        is themed via the CSS variables injected above, so only its
        stable identity (color, radius) lives here; the dynamic geometry
        (opacity/width/top/left) stays inline in JS.
        """
        return (
            # Firefox — none hides the bar but keeps scrolling.
            "html{scrollbar-width:none;}"
            # WebKit — zero size + display:none leaves the engine nothing
            # to render or hover-grow on every scroll surface.
            "::-webkit-scrollbar{width:0;height:0;display:none}"
            # Custom scroll-indicator thumb — JS-built overlay on
            # [data-neony-scroll] surfaces.  Color follows the theme via
            # the CSS vars; geometry is set inline by the JS engine.
            ".neony-scroll-thumb{background-color:var(--color-text-secondary);border-radius:999px;}"
        )

    def to_css(self) -> str:
        """Generate the ``:root { --color-*: ...; }`` block plus scrollbar rules."""
        tokens: list[str] = []
        for name in type(self).model_fields:
            if name == "mode":
                continue
            tokens.append(f"--color-{name.replace('_', '-')}: {getattr(self, name)};")
        return ":root { " + " ".join(tokens) + " } " + self._scrollbar_css()

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
        """Cycle through the available modes (:attr:`modes`)."""
        order = type(self).modes
        self.set_mode(order[(order.index(self.mode) + 1) % len(order)])


DARK = Theme(mode="dark", **_DARK)
LIGHT = Theme(mode="light", **_LIGHT)
DEEP_BLUE = Theme(mode="deep-blue", **_DEEP_BLUE)
