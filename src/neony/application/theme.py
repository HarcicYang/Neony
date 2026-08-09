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

from neony.dom.css import BoxShadow, Color, Shadow


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

    # --- semantic tokens (Color values / rgba) ---
    bg: Color
    surface: Color
    surface_raised: Color
    text_primary: Color
    text_secondary: Color
    accent: Color
    accent_dim: Color
    danger: Color
    success: Color
    border: Color
    #: Box-shadow token — typed as BoxShadow, NOT a plain str.
    shadow: BoxShadow
    #: Text colour on a filled ``accent`` background (white across built-ins).
    on_accent: Color
    #: Text colour on a filled ``danger`` background (white across built-ins).
    on_danger: Color

    # --- background overlay (theme colour at ~70% for dimming) ---
    bg_overlay: Color

    # --- glass tokens (opt-in frosted look, per-theme) ---
    surface_glass: Color
    surface_raised_glass: Color
    border_glass: Color
    accent_glass: Color
    danger_glass: Color
    success_glass: Color
    surface_glass_bg: Color
    surface_panel_glass_bg: Color
    accent_glass_bg: Color
    danger_glass_bg: Color

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
        """Highlight border colour for a semantic role (``var(--color-*-glass)``).

        Resolved from the :data:`stub` token namespace — no raw ``var()``
        strings here; the token's ``var`` field carries the CSS name.
        """
        tok = {
            "accent": stub.accent_glass,
            "danger": stub.danger_glass,
            "success": stub.success_glass,
        }.get(role, stub.border_glass)
        return f"var({tok.var})"

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
    bg=Color(hex="#0d0d12"),
    surface=Color(hex="#1a1a24"),
    surface_raised=Color(hex="#242436"),
    text_primary=Color(hex="#e8e8ed"),
    text_secondary=Color(hex="#707088"),
    accent=Color(hex="#6c8cff"),
    accent_dim=Color(hex="#5570cc"),
    danger=Color(hex="#ff6b6b"),
    success=Color(hex="#4ecdc4"),
    border=Color(rgba=(255, 255, 255, 0.06)),
    shadow=BoxShadow(layers=[Shadow(x=0, y=8, blur=32, color=Color(rgba=(0, 0, 0, 0.25)))]),
    on_accent=Color(hex="#ffffff"),
    on_danger=Color(hex="#ffffff"),
    bg_overlay=Color(rgba=(13, 13, 18, 0.7)),
    surface_glass=Color(rgba=(52, 52, 56, 0.92)),
    surface_raised_glass=Color(rgba=(60, 60, 64, 0.92)),
    border_glass=Color(rgba=(255, 255, 255, 0.08)),
    accent_glass=Color(rgba=(108, 140, 255, 0.25)),
    danger_glass=Color(rgba=(255, 107, 107, 0.25)),
    success_glass=Color(rgba=(78, 205, 196, 0.25)),
    surface_glass_bg=Color(rgba=(40, 40, 44, 0.60)),
    surface_panel_glass_bg=Color(rgba=(40, 40, 44, 0.85)),
    accent_glass_bg=Color(rgba=(74, 144, 217, 0.60)),
    danger_glass_bg=Color(rgba=(255, 107, 107, 0.60)),
)

LIGHT = Theme(
    mode="light",
    bg=Color(hex="#f4f5f7"),
    surface=Color(hex="#ffffff"),
    surface_raised=Color(hex="#ebebeb"),
    text_primary=Color(hex="#1a1a2e"),
    text_secondary=Color(hex="#5a5a72"),
    accent=Color(hex="#3a7bc8"),
    accent_dim=Color(hex="#2e6bb0"),
    danger=Color(hex="#d9534f"),
    success=Color(hex="#2fa89a"),
    border=Color(rgba=(0, 0, 0, 0.08)),
    shadow=BoxShadow(layers=[Shadow(x=0, y=8, blur=32, color=Color(rgba=(0, 0, 0, 0.08)))]),
    on_accent=Color(hex="#ffffff"),
    on_danger=Color(hex="#ffffff"),
    bg_overlay=Color(rgba=(244, 245, 247, 0.7)),
    surface_glass=Color(rgba=(255, 255, 255, 0.88)),
    surface_raised_glass=Color(rgba=(255, 255, 255, 0.88)),
    border_glass=Color(rgba=(0, 0, 0, 0.12)),
    accent_glass=Color(rgba=(58, 123, 200, 0.2)),
    danger_glass=Color(rgba=(217, 83, 79, 0.2)),
    success_glass=Color(rgba=(47, 168, 154, 0.2)),
    surface_glass_bg=Color(rgba=(255, 255, 255, 0.60)),
    surface_panel_glass_bg=Color(rgba=(255, 255, 255, 0.85)),
    accent_glass_bg=Color(rgba=(58, 123, 200, 0.60)),
    danger_glass_bg=Color(rgba=(217, 83, 79, 0.60)),
)

DEEP_BLUE = Theme(
    mode="deep-blue",
    bg=Color(hex="#1a1a2e"),
    surface=Color(hex="#252540"),
    surface_raised=Color(hex="#2e2e4a"),
    text_primary=Color(hex="#ffffff"),
    text_secondary=Color(hex="#8080a0"),
    accent=Color(hex="#4a90d9"),
    accent_dim=Color(hex="#3a7bc8"),
    danger=Color(hex="#ff6b6b"),
    success=Color(hex="#4ecdc4"),
    border=Color(rgba=(255, 255, 255, 0.06)),
    shadow=BoxShadow(layers=[Shadow(x=0, y=8, blur=32, color=Color(rgba=(0, 0, 0, 0.12)))]),
    on_accent=Color(hex="#ffffff"),
    on_danger=Color(hex="#ffffff"),
    bg_overlay=Color(rgba=(26, 26, 46, 0.7)),
    surface_glass=Color(rgba=(54, 54, 92, 0.92)),
    surface_raised_glass=Color(rgba=(64, 64, 104, 0.92)),
    border_glass=Color(rgba=(255, 255, 255, 0.08)),
    accent_glass=Color(rgba=(74, 144, 217, 0.25)),
    danger_glass=Color(rgba=(255, 107, 107, 0.25)),
    success_glass=Color(rgba=(78, 205, 196, 0.25)),
    surface_glass_bg=Color(rgba=(34, 34, 74, 0.60)),
    surface_panel_glass_bg=Color(rgba=(34, 34, 74, 0.85)),
    accent_glass_bg=Color(rgba=(74, 144, 217, 0.60)),
    danger_glass_bg=Color(rgba=(255, 107, 107, 0.60)),
)


class _ThemeStub(Theme):
    """Token namespace — references to theme tokens as :class:`Color` objects.

    Inherit-and-override: each color field from :class:`Theme` (which on a
    preset *instance* holds a concrete :class:`Color`) is overridden here as a
    ``ClassVar[Color]`` pointing at the token's ``Color(var="--color-<name>")``
    reference.  A ``ClassVar`` overriding an instance variable always trips
    pyrefly's ``[bad-override]`` (LSP); the rule is disabled project-wide in
    ``pyproject.toml`` (``[tool.pyrefly.errors] bad-override = false``), so
    the rows carry no inline ignores and the resolved type stays ``Color``.

    Exposed via the single instance :data:`stub` (this class stays private).
    ``stub.text_primary`` carries full static typing + autocomplete: a typo
    is both a type-check error and a runtime ``AttributeError`` (never a
    silently-broken CSS string). The instance never registers itself, so the
    preset registry is not polluted.
    """

    def model_post_init(self, __context: object) -> None:
        """No-op — the stub is a token namespace, never a registered preset."""

    mode: str = "stub"

    bg: ClassVar[Color] = Color(var="--color-bg")
    surface: ClassVar[Color] = Color(var="--color-surface")
    surface_raised: ClassVar[Color] = Color(var="--color-surface-raised")
    text_primary: ClassVar[Color] = Color(var="--color-text-primary")
    text_secondary: ClassVar[Color] = Color(var="--color-text-secondary")
    accent: ClassVar[Color] = Color(var="--color-accent")
    accent_dim: ClassVar[Color] = Color(var="--color-accent-dim")
    danger: ClassVar[Color] = Color(var="--color-danger")
    success: ClassVar[Color] = Color(var="--color-success")
    border: ClassVar[Color] = Color(var="--color-border")
    #: Parent field is ``BoxShadow``; here it is the ``--color-shadow``
    #: *token* reference — a deliberate cross-type override.
    shadow: ClassVar[Color] = Color(var="--color-shadow")
    on_accent: ClassVar[Color] = Color(var="--color-on-accent")
    on_danger: ClassVar[Color] = Color(var="--color-on-danger")
    bg_overlay: ClassVar[Color] = Color(var="--color-bg-overlay")
    surface_glass: ClassVar[Color] = Color(var="--color-surface-glass")
    surface_raised_glass: ClassVar[Color] = Color(var="--color-surface-raised-glass")
    border_glass: ClassVar[Color] = Color(var="--color-border-glass")
    accent_glass: ClassVar[Color] = Color(var="--color-accent-glass")
    danger_glass: ClassVar[Color] = Color(var="--color-danger-glass")
    success_glass: ClassVar[Color] = Color(var="--color-success-glass")
    surface_glass_bg: ClassVar[Color] = Color(var="--color-surface-glass-bg")
    surface_panel_glass_bg: ClassVar[Color] = Color(var="--color-surface-panel-glass-bg")
    accent_glass_bg: ClassVar[Color] = Color(var="--color-accent-glass-bg")
    danger_glass_bg: ClassVar[Color] = Color(var="--color-danger-glass-bg")


#: Public token namespace — reference any theme token as a typed Color object.
stub = _ThemeStub()
