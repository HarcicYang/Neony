"""Immutable semantic-color theme presets.

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
    """Semantic color palette for one display mode.

    Frozen and default-free: a ``Theme`` always describes one concrete palette,
    so every token must be supplied at construction (there is no meaningful
    empty/default instance). Constructing an instance auto-registers it under
    its ``mode`` via :meth:`model_post_init`; :meth:`as` and :meth:`next` then
    look presets up by name.
    """

    model_config = ConfigDict(frozen=True)

    # Insertion-ordered map of registered ``mode`` -> preset instance.
    # ClassVar, so it is not a model field and never serializes into the CSS
    # block. Built-in presets are constructed first; user presets registered
    # later append naturally and join the :meth:`next` cycle.
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
    #: The accent hue shifted toward ``bg`` (see
    #: :func:`secondary_accent`) — the family color a step away from
    #: the accent, for secondary emphasis on accent surfaces.
    accent_secondary: Color
    danger: Color
    success: Color
    border: Color
    #: Box-shadow token — typed as BoxShadow, NOT a plain str.
    shadow: BoxShadow
    #: Text color on a filled ``accent`` background (white across built-ins).
    on_accent: Color
    #: Text color on a filled ``danger`` background (white across built-ins).
    on_danger: Color

    # --- background overlay (theme color at ~70% for dimming) ---
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
        """Highlight border color for a semantic role (``var(--color-*-glass)``).

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
    def focus_glow(role: str = "accent") -> BoxShadow:
        """3px focus-ring halo using the role's glass token (neutral
        roles resolve to the subtle border glass) — a typed
        :class:`BoxShadow` ready for ``Styles.box_shadow``."""
        tok = {
            "accent": stub.accent_glass,
            "danger": stub.danger_glass,
            "success": stub.success_glass,
        }.get(role, stub.border_glass)
        return BoxShadow(layers=[Shadow(x=0, y=0, blur=0, spread="3px", color=tok)])

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


def _shift(hex_color: str, toward: str, t: float = 0.25) -> str:
    """Blend *hex_color* toward *toward* by *t* (linear RGB)."""
    base = (int(hex_color[1:3], 16), int(hex_color[3:5], 16), int(hex_color[5:7], 16))
    target = (int(toward[1:3], 16), int(toward[3:5], 16), int(toward[5:7], 16))
    blended = tuple(round(bc + (tc - bc) * t) for bc, tc in zip(base, target, strict=True))
    return "#{:02x}{:02x}{:02x}".format(*blended)


def secondary_accent(accent: Color, bg: Color, t: float = 0.25) -> Color:
    """Derive a theme's secondary accent: *accent* shifted toward *bg*
    by *t*.

    The family hue stays intact while the tone moves away from the
    accent itself — deepened on dark presets, lifted on light ones —
    so surfaces tinted with it (a ``from_me`` bubble's code well,
    table bands) always read next to the accent.  Custom presets can
    build their ``accent_secondary`` with this instead of picking a
    second color.
    """
    a = accent.hex or ""
    o = bg.hex or ""
    if len(a) != 7 or len(o) != 7:
        raise ValueError("secondary_accent expects hex Colors (#rrggbb)")
    return Color(hex=_shift(a, o, t))


def _theme(
    mode: str,
    *,
    bg: str,
    surface: str,
    raised: str,
    text: str,
    muted: str,
    accent: str,
    accent_dim: str,
    danger: str,
    success: str,
    border: tuple[int, int, int, float],
    shadow: tuple[int, int, int, tuple[int, int, int, float]],
    on_accent: str,
    bg_overlay: tuple[int, int, int, float],
    glass: tuple[int, int, int, float],
    raised_glass: tuple[int, int, int, float],
    border_glass: tuple[int, int, int, float],
    accent_glass: tuple[int, int, int, float],
    danger_glass: tuple[int, int, int, float],
    success_glass: tuple[int, int, int, float],
    glass_bg: tuple[int, int, int, float],
    panel_glass_bg: tuple[int, int, int, float],
    accent_glass_bg: tuple[int, int, int, float],
    danger_glass_bg: tuple[int, int, int, float],
) -> Theme:
    """Build a complete theme-family preset with explicit semantic tokens."""
    sx, sy, sb, sc = shadow
    return Theme(
        mode=mode,
        bg=Color(hex=bg),
        surface=Color(hex=surface),
        surface_raised=Color(hex=raised),
        text_primary=Color(hex=text),
        text_secondary=Color(hex=muted),
        accent=Color(hex=accent),
        accent_dim=Color(hex=accent_dim),
        # Derived, not chosen: the accent hue shifted toward the page
        # background — deepened on dark presets, lifted on light ones —
        # so it always reads next to the accent itself.
        accent_secondary=Color(hex=_shift(accent, bg)),
        danger=Color(hex=danger),
        success=Color(hex=success),
        border=Color(rgba=border),
        shadow=BoxShadow(layers=[Shadow(x=sx, y=sy, blur=sb, color=Color(rgba=sc))]),
        on_accent=Color(hex=on_accent),
        on_danger=Color(hex="#ffffff"),
        bg_overlay=Color(rgba=bg_overlay),
        surface_glass=Color(rgba=glass),
        surface_raised_glass=Color(rgba=raised_glass),
        border_glass=Color(rgba=border_glass),
        accent_glass=Color(rgba=accent_glass),
        danger_glass=Color(rgba=danger_glass),
        success_glass=Color(rgba=success_glass),
        surface_glass_bg=Color(rgba=glass_bg),
        surface_panel_glass_bg=Color(rgba=panel_glass_bg),
        accent_glass_bg=Color(rgba=accent_glass_bg),
        danger_glass_bg=Color(rgba=danger_glass_bg),
    )


# Four visual families, each with a paired light and dark material.
NIGHTGLOW_DARK = _theme(
    "nightglow-dark",
    bg="#17191c",
    surface="#23272c",
    raised="#2d3339",
    text="#edf0f2",
    muted="#89939c",
    accent="#54b9c2",
    accent_dim="#398c95",
    danger="#e87878",
    success="#70c99a",
    border=(232, 240, 244, 0.11),
    shadow=(0, 24, 70, (0, 0, 0, 0.42)),
    on_accent="#ffffff",
    bg_overlay=(23, 25, 28, 0.72),
    glass=(31, 35, 39, 0.78),
    raised_glass=(45, 51, 57, 0.84),
    border_glass=(232, 240, 244, 0.15),
    accent_glass=(84, 185, 194, 0.26),
    danger_glass=(232, 120, 120, 0.22),
    success_glass=(112, 201, 154, 0.2),
    glass_bg=(31, 35, 39, 0.64),
    panel_glass_bg=(35, 39, 44, 0.86),
    accent_glass_bg=(84, 185, 194, 0.58),
    danger_glass_bg=(232, 120, 120, 0.58),
)
NIGHTGLOW_LIGHT = _theme(
    "nightglow-light",
    bg="#edf1f1",
    surface="#ffffff",
    raised="#e5ebeb",
    text="#172426",
    muted="#617376",
    accent="#247d85",
    accent_dim="#1d646b",
    danger="#b95758",
    success="#27875f",
    border=(23, 36, 38, 0.14),
    shadow=(0, 20, 56, (29, 57, 58, 0.16)),
    on_accent="#ffffff",
    bg_overlay=(237, 241, 241, 0.74),
    glass=(248, 251, 250, 0.82),
    raised_glass=(255, 255, 255, 0.9),
    border_glass=(23, 36, 38, 0.16),
    accent_glass=(36, 125, 133, 0.2),
    danger_glass=(185, 87, 88, 0.18),
    success_glass=(39, 135, 95, 0.16),
    glass_bg=(248, 251, 250, 0.7),
    panel_glass_bg=(255, 255, 255, 0.9),
    accent_glass_bg=(36, 125, 133, 0.56),
    danger_glass_bg=(185, 87, 88, 0.56),
)
PLANET_PLAZA_DARK = _theme(
    "planet-plaza-dark",
    bg="#111827",
    surface="#223148",
    raised="#2d4260",
    text="#edf4ff",
    muted="#8da0ba",
    accent="#71d5c4",
    accent_dim="#4cae9f",
    danger="#ff8c92",
    success="#82d9ad",
    border=(184, 215, 255, 0.16),
    shadow=(0, 28, 90, (0, 0, 0, 0.46)),
    on_accent="#ffffff",
    bg_overlay=(17, 24, 39, 0.74),
    glass=(31, 49, 76, 0.62),
    raised_glass=(45, 66, 96, 0.78),
    border_glass=(184, 215, 255, 0.2),
    accent_glass=(113, 213, 196, 0.25),
    danger_glass=(255, 140, 146, 0.22),
    success_glass=(130, 217, 173, 0.2),
    glass_bg=(31, 49, 76, 0.56),
    panel_glass_bg=(34, 49, 72, 0.82),
    accent_glass_bg=(113, 213, 196, 0.56),
    danger_glass_bg=(255, 140, 146, 0.56),
)
PLANET_PLAZA_LIGHT = _theme(
    "planet-plaza-light",
    bg="#eef1f8",
    surface="#ffffff",
    raised="#e5eaf5",
    text="#1a2235",
    muted="#68738b",
    accent="#5068f2",
    accent_dim="#4055c9",
    danger="#d3546b",
    success="#239b83",
    border=(49, 67, 112, 0.15),
    shadow=(0, 22, 64, (63, 78, 122, 0.16)),
    on_accent="#ffffff",
    bg_overlay=(238, 241, 248, 0.74),
    glass=(249, 251, 255, 0.78),
    raised_glass=(255, 255, 255, 0.9),
    border_glass=(49, 67, 112, 0.17),
    accent_glass=(80, 104, 242, 0.18),
    danger_glass=(211, 84, 107, 0.18),
    success_glass=(35, 155, 131, 0.16),
    glass_bg=(249, 251, 255, 0.68),
    panel_glass_bg=(255, 255, 255, 0.88),
    accent_glass_bg=(80, 104, 242, 0.56),
    danger_glass_bg=(211, 84, 107, 0.56),
)
EMBER_ZONE_DARK = _theme(
    "ember-zone-dark",
    bg="#080a09",
    surface="#131914",
    raised="#1b241b",
    text="#e6eee4",
    muted="#788878",
    accent="#e3a94f",
    accent_dim="#a56d22",
    danger="#c9655e",
    success="#68b98c",
    border=(185, 215, 178, 0.12),
    shadow=(0, 30, 76, (0, 0, 0, 0.62)),
    on_accent="#ffffff",
    bg_overlay=(8, 10, 9, 0.78),
    glass=(12, 17, 13, 0.86),
    raised_glass=(27, 36, 27, 0.92),
    border_glass=(185, 215, 178, 0.14),
    accent_glass=(227, 169, 79, 0.2),
    danger_glass=(201, 101, 94, 0.18),
    success_glass=(104, 185, 140, 0.16),
    glass_bg=(12, 17, 13, 0.78),
    panel_glass_bg=(19, 25, 19, 0.94),
    accent_glass_bg=(227, 169, 79, 0.54),
    danger_glass_bg=(201, 101, 94, 0.54),
)
EMBER_ZONE_LIGHT = _theme(
    "ember-zone-light",
    bg="#e8e5dc",
    surface="#fcf8ee",
    raised="#eee9dd",
    text="#2c271e",
    muted="#756d5c",
    accent="#a66d22",
    accent_dim="#82551a",
    danger="#ae554c",
    success="#377b59",
    border=(62, 52, 34, 0.16),
    shadow=(0, 20, 54, (70, 57, 32, 0.18)),
    on_accent="#ffffff",
    bg_overlay=(232, 229, 220, 0.74),
    glass=(245, 241, 232, 0.82),
    raised_glass=(252, 248, 238, 0.92),
    border_glass=(62, 52, 34, 0.18),
    accent_glass=(166, 109, 34, 0.18),
    danger_glass=(174, 84, 76, 0.18),
    success_glass=(55, 123, 89, 0.16),
    glass_bg=(245, 241, 232, 0.72),
    panel_glass_bg=(252, 248, 238, 0.92),
    accent_glass_bg=(166, 109, 34, 0.54),
    danger_glass_bg=(174, 84, 76, 0.54),
)
CYBERANGEL_DARK = _theme(
    "cyberangel-dark",
    bg="#090b14",
    surface="#141827",
    raised="#1d2335",
    text="#f4f7ff",
    muted="#9aa6c4",
    accent="#8b7cff",
    accent_dim="#6457d8",
    danger="#ff6f8f",
    success="#39d6b4",
    border=(190, 205, 255, 0.12),
    shadow=(0, 28, 90, (0, 0, 0, 0.48)),
    on_accent="#ffffff",
    bg_overlay=(9, 11, 20, 0.72),
    glass=(20, 24, 39, 0.78),
    raised_glass=(29, 35, 53, 0.82),
    border_glass=(190, 205, 255, 0.16),
    accent_glass=(139, 124, 255, 0.32),
    danger_glass=(255, 111, 143, 0.28),
    success_glass=(57, 214, 180, 0.26),
    glass_bg=(20, 24, 39, 0.62),
    panel_glass_bg=(20, 24, 39, 0.78),
    accent_glass_bg=(139, 124, 255, 0.62),
    danger_glass_bg=(255, 111, 143, 0.62),
)
CYBERANGEL_LIGHT = _theme(
    "cyberangel-light",
    bg="#eef0f8",
    surface="#ffffff",
    raised="#e7e9f5",
    text="#202238",
    muted="#6e7290",
    accent="#6a58de",
    accent_dim="#5142b8",
    danger="#c65373",
    success="#168d79",
    border=(65, 70, 121, 0.16),
    shadow=(0, 22, 70, (67, 72, 124, 0.18)),
    on_accent="#ffffff",
    bg_overlay=(238, 240, 248, 0.74),
    glass=(248, 249, 255, 0.78),
    raised_glass=(255, 255, 255, 0.92),
    border_glass=(65, 70, 121, 0.18),
    accent_glass=(106, 88, 222, 0.2),
    danger_glass=(198, 83, 115, 0.18),
    success_glass=(22, 141, 121, 0.16),
    glass_bg=(248, 249, 255, 0.68),
    panel_glass_bg=(255, 255, 255, 0.9),
    accent_glass_bg=(106, 88, 222, 0.56),
    danger_glass_bg=(198, 83, 115, 0.56),
)

# Compatibility aliases: the historical names remain importable.
DARK = NIGHTGLOW_DARK
LIGHT = NIGHTGLOW_LIGHT
DEEP_BLUE = PLANET_PLAZA_DARK


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
    #: The accent hue shifted toward the page background — secondary
    #: emphasis (markdown code well, links, rules, table bands on
    #: ``from_me`` bubbles) that always reads next to the accent.
    accent_secondary: ClassVar[Color] = Color(var="--color-accent-secondary")
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
