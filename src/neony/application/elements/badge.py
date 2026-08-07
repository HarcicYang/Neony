"""Badge component — a small status label or corner count.

Two shapes share one class:

- ``position="inline"`` (default) — a pill that flows with text, tinted by
  ``variant`` (accent / danger / success / neutral).
- ``position="top-right"`` etc. — the same pill absolutely positioned as a
  count badge.  The component positions itself relative to its parent; the
  *caller* must put it inside a ``position: relative`` container (an
  Avatar/Button wrapper).  ``box-shadow: 0 0 0 2px var(--color-bg)`` punches
  a hole around the badge so it reads against any background.

Integer content gets two conveniences: counts above ``max`` (default 99)
collapse to ``"99+"``, and a zero count hides the badge unless
``show_zero=True`` (the node stays mounted so it can toggle back).
``dot=True`` drops the text for a status dot.
"""

from __future__ import annotations

from typing import Literal

from neony.dom import Color, Span, Styles

from .base import Component

_Variant = Literal["accent", "danger", "success", "neutral"]
_Position = Literal["inline", "top-right", "top-left", "bottom-right", "bottom-left"]

_BASE = Styles(
    display="inline-flex",
    align_items="center",
    justify_content="center",
    gap="4px",
    padding="2px 8px",
    border_radius="999px",
    font_size="11px",
    font_weight="600",
    line_height="1",
    white_space="nowrap",
)

# Inline pill colours — variant tints the background; neutral is subtle.
_VARIANT_BG: dict[str, str] = {
    "accent": "var(--color-accent)",
    "danger": "var(--color-danger)",
    "success": "var(--color-success)",
    "neutral": "var(--color-surface-raised)",
}
_VARIANT_FG: dict[str, str] = {
    "accent": "white",
    "danger": "white",
    "success": "white",
    "neutral": "var(--color-text-secondary)",
}

# Corner-badge offsets — anchor-relative to the parent container.
_CORNER: dict[str, Styles] = {
    "top-right": Styles(top="-6px", right="-6px"),
    "top-left": Styles(top="-6px", left="-6px"),
    "bottom-right": Styles(bottom="-6px", right="-6px"),
    "bottom-left": Styles(bottom="-6px", left="-6px"),
}

_DOT = Styles(
    display="inline-block",
    width="8px",
    height="8px",
    border_radius="999px",
    background_color=Color(var="--color-accent"),
)


def _color(value: str) -> Color:
    """Build a ``Color`` from a token (``var(--color-x)``) or a literal
    (``white``).  Tokens carry their custom-property name; literals land
    as a named CSS colour."""
    if value.startswith("var("):
        return Color(var=value[4:].rstrip(")").strip())
    return Color(name=value)


class Badge(Component):
    """A status label or corner count.

    - ``content`` — text label or an integer count (first positional arg).
    - ``variant`` — ``"neutral"`` (default) / ``"accent"`` / ``"danger"`` /
      ``"success"``.
    - ``dot`` — render a coloured status dot instead of text.
    - ``position`` — ``"inline"`` (default) or a corner
      (``"top-right"`` …); corner positioning assumes a
      ``position: relative`` parent.
    - ``overlap`` — push a corner badge further out (``-12px``) to overlap
      the parent's edge.
    - ``show_zero`` — keep a zero integer count visible (hidden by default).
    - ``max`` — clamp an integer count above this to ``"{max}+"`` (default 99).
    """

    def __init__(
        self,
        content: str | int = "",
        *,
        variant: _Variant = "neutral",
        dot: bool = False,
        position: _Position = "inline",
        overlap: bool = False,
        show_zero: bool = False,
        max: int = 99,
    ) -> None:
        super().__init__()
        self._content = content
        self._variant = variant
        self._dot = dot
        self._position = position
        self._overlap = overlap
        self._show_zero = show_zero
        self._max = max
        self._root = Span()
        self._apply()

    # ---- state ----

    @property
    def content(self) -> str | int:
        return self._content

    @content.setter
    def content(self, value: str | int) -> None:
        self._content = value
        self._apply()

    @property
    def variant(self) -> _Variant:
        return self._variant

    @variant.setter
    def variant(self, value: _Variant) -> None:
        self._variant = value
        self._apply()

    @property
    def dot(self) -> bool:
        return self._dot

    @dot.setter
    def dot(self, value: bool) -> None:
        self._dot = value
        self._apply()

    # ---- internals ----

    def _format_content(self) -> str | None:
        """The visible text, or ``None`` to omit it (dot / empty)."""
        if self._dot:
            return None
        if isinstance(self._content, int):
            if self._content > self._max:
                return f"{self._max}+"
            return str(self._content)
        return str(self._content)

    def _hidden(self) -> bool:
        # A zero integer count hides the badge unless show_zero is set.
        return isinstance(self._content, int) and self._content == 0 and not self._show_zero

    def _build_styles(self) -> Styles:
        if self._dot:
            # A bare status dot: rounded, coloured by variant, no text.
            return _DOT.model_copy(update={"background_color": _color(_VARIANT_BG[self._variant])})
        styles = _BASE.model_copy(
            update={
                "background_color": _color(_VARIANT_BG[self._variant]),
                "color": _color(_VARIANT_FG[self._variant]),
            }
        )
        if self._position != "inline":
            # Compact pill, absolutely positioned in the caller's relative
            # container, with a punched-out ring so it reads on any bg.
            offset = "-12px" if self._overlap else "-6px"
            corner = _CORNER[self._position]
            corner_update: dict[str, str] = {}
            for side in ("top", "bottom", "left", "right"):
                if getattr(corner, side, None) is not None:
                    corner_update[side] = offset
            styles = styles.model_copy(
                update={
                    "position": "absolute",
                    "z_index": 10,
                    "padding": "0 6px",
                    "min_width": "18px",
                    "height": "18px",
                    "box_shadow": "0 0 0 2px var(--color-bg)",
                    **corner_update,
                }
            )
        return styles

    def _apply(self) -> None:
        """Re-derive styles + children from the current state."""
        styles = self._build_styles()
        if self._hidden():
            styles = styles.model_copy(update={"display": "none"})
        self._root.styles = styles
        text = self._format_content()
        self._root.container = [] if text is None else [text]
