"""Immutable semantic-colour theme presets.

Each preset is a frozen :class:`Theme` instance; constructing one auto-registers
it under its ``mode`` in a class-level registry. Tokens are exposed to CSS as
custom properties (``--color-*``) on ``:root``; components reference them via
``Color(var=...)`` so a theme switch just re-injects the block and the browser
redraws — no DOM diff. Glass tokens (``surface_glass`` etc.) are per-theme, so
the frosted look always stays in family with the palette.

Switching themes swaps the active reference (see ``App.set_theme``) rather than
mutating an instance in place — presets are immutable, and user-defined presets
register themselves the same way the built-ins do.
"""

from __future__ import annotations

from typing import ClassVar

from pydantic import BaseModel, ConfigDict


class Theme(BaseModel):
    """Semantic colour palette for one display mode.

    Frozen and default-free: a ``Theme`` always describes one concrete palette,
    so every token must be supplied at construction (there is no meaningful
    empty/default instance). Constructing an instance auto-registers it under
    its ``mode`` via :meth:`model_post_init`; :meth:`as` and :meth:`next` then
    look presets up by name.
    """

    model_config = ConfigDict(frozen=True)

    #: Insertion-ordered map of registered ``mode`` -> preset instance.
    #: ClassVar, so it is not a model field and never serialises into the CSS
    #: block. Built-in presets are constructed first; user presets registered
    #: later append naturally and join the :meth:`next` cycle.
    _registry: ClassVar[dict[str, Theme]] = {}

    def model_post_init(self, __context: object) -> None:
        """Auto-register this instance under its ``mode`` once it is built."""
        type(self)._registry[self.mode] = self

    mode: str

    # --- semantic tokens (hex strings / rgba) ---
    bg: str
    surface: str
    surface_raised: str
    text_primary: str
    text_secondary: str
    accent: str
    accent_dim: str
    danger: str
    success: str
    border: str
    shadow: str
    #: Text colour on a filled ``accent`` background (white across built-ins).
    on_accent: str
    #: Text colour on a filled ``danger`` background (white across built-ins).
    on_danger: str

    # --- background overlay (theme colour at ~70% for dimming) ---
    bg_overlay: str

    # --- glass tokens (opt-in frosted look, per-theme) ---
    surface_glass: str
    surface_raised_glass: str
    border_glass: str
    accent_glass: str
    danger_glass: str
    success_glass: str
    surface_glass_bg: str
    surface_panel_glass_bg: str
    accent_glass_bg: str
    danger_glass_bg: str

    @classmethod
    def modes(cls) -> tuple[str, ...]:
        """Registered mode names in the order their presets were constructed.

        A derived view over the registry — not a hardcoded tuple — so user
        presets registered later append naturally and :meth:`next` cycles them.
        """
        return tuple(cls._registry)

    @staticmethod
    def mode_label(mode: str) -> str:
        """Human label describing the mode that follows *mode* in the
        toggle cycle — what a theme-toggle button promises next, e.g.
        ``Theme.mode_label("dark") == "Light mode"``.  Raises
        ``ValueError`` for unknown modes."""
        order = Theme.modes()
        nxt = order[(order.index(mode) + 1) % len(order)]
        return f"{nxt.replace('-', ' ').title()} mode"

    @classmethod
    def get(cls, name: str) -> Theme:
        """Return the registered preset for *name* (single dict read; no fallback).

        Raises ``KeyError`` if no preset was ever constructed with that mode.
        """
        return cls._registry[name]

    def next(self) -> Theme:
        """Return the preset that follows this one in :meth:`modes` (insertion) order.

        Reads ``self.mode`` to find the next mode name, then resolves it via
        the registry — no parameters, returns a :class:`Theme` instance.
        """
        order = type(self).modes()
        nxt = order[(order.index(self.mode) + 1) % len(order)]
        return type(self).get(nxt)

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


DARK = Theme(
    mode="dark",
    bg="#0d0d12",
    surface="#1a1a24",
    surface_raised="#242436",
    text_primary="#e8e8ed",
    text_secondary="#707088",
    accent="#6c8cff",
    accent_dim="#5570cc",
    danger="#ff6b6b",
    success="#4ecdc4",
    border="rgba(255, 255, 255, 0.06)",
    shadow="0 8px 32px rgba(0, 0, 0, 0.25)",
    on_accent="#ffffff",
    on_danger="#ffffff",
    bg_overlay="rgba(13, 13, 18, 0.7)",
    surface_glass="rgba(52, 52, 56, 0.92)",
    surface_raised_glass="rgba(60, 60, 64, 0.92)",
    border_glass="rgba(255, 255, 255, 0.08)",
    accent_glass="rgba(108, 140, 255, 0.25)",
    danger_glass="rgba(255, 107, 107, 0.25)",
    success_glass="rgba(78, 205, 196, 0.25)",
    surface_glass_bg="rgba(40, 40, 44, 0.60)",
    surface_panel_glass_bg="rgba(40, 40, 44, 0.85)",
    accent_glass_bg="rgba(74, 144, 217, 0.60)",
    danger_glass_bg="rgba(255, 107, 107, 0.60)",
)

LIGHT = Theme(
    mode="light",
    bg="#f4f5f7",
    surface="#ffffff",
    surface_raised="#ebebeb",
    text_primary="#1a1a2e",
    text_secondary="#5a5a72",
    accent="#3a7bc8",
    accent_dim="#2e6bb0",
    danger="#d9534f",
    success="#2fa89a",
    border="rgba(0, 0, 0, 0.08)",
    shadow="0 8px 32px rgba(0, 0, 0, 0.08)",
    on_accent="#ffffff",
    on_danger="#ffffff",
    bg_overlay="rgba(244, 245, 247, 0.7)",
    surface_glass="rgba(255, 255, 255, 0.88)",
    surface_raised_glass="rgba(255, 255, 255, 0.88)",
    border_glass="rgba(0, 0, 0, 0.12)",
    accent_glass="rgba(58, 123, 200, 0.2)",
    danger_glass="rgba(217, 83, 79, 0.2)",
    success_glass="rgba(47, 168, 154, 0.2)",
    surface_glass_bg="rgba(255, 255, 255, 0.60)",
    surface_panel_glass_bg="rgba(255, 255, 255, 0.85)",
    accent_glass_bg="rgba(58, 123, 200, 0.60)",
    danger_glass_bg="rgba(217, 83, 79, 0.60)",
)

DEEP_BLUE = Theme(
    mode="deep-blue",
    bg="#1a1a2e",
    surface="#252540",
    surface_raised="#2e2e4a",
    text_primary="#ffffff",
    text_secondary="#8080a0",
    accent="#4a90d9",
    accent_dim="#3a7bc8",
    danger="#ff6b6b",
    success="#4ecdc4",
    border="rgba(255, 255, 255, 0.06)",
    shadow="0 8px 32px rgba(0, 0, 0, 0.12)",
    on_accent="#ffffff",
    on_danger="#ffffff",
    bg_overlay="rgba(26, 26, 46, 0.7)",
    surface_glass="rgba(54, 54, 92, 0.92)",
    surface_raised_glass="rgba(64, 64, 104, 0.92)",
    border_glass="rgba(255, 255, 255, 0.08)",
    accent_glass="rgba(74, 144, 217, 0.25)",
    danger_glass="rgba(255, 107, 107, 0.25)",
    success_glass="rgba(78, 205, 196, 0.25)",
    surface_glass_bg="rgba(34, 34, 74, 0.60)",
    surface_panel_glass_bg="rgba(34, 34, 74, 0.85)",
    accent_glass_bg="rgba(74, 144, 217, 0.60)",
    danger_glass_bg="rgba(255, 107, 107, 0.60)",
)
