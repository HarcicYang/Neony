"""Checkbox component — custom-styled, stateful, chainable events.

The native WebKitGTK checkbox is replaced with a themed rounded box:
``appearance: none`` strips the system look, and the checked state is
driven by the component itself — accent background + white check SVG.
"""

from __future__ import annotations

import urllib.parse

from neony.application.theme import Theme
from neony.dom import Color, DomEvent, Span, Styles, Transition
from neony.dom import Input as _InputElem
from neony.dom import Label as _LabelElem

from .base import Component

_ROW = Styles(
    display="flex",
    align_items="center",
    gap="10px",
    font_size="15px",
    cursor="pointer",
    color=Color(var="--color-text-primary"),
)

_BOX = Styles(
    width="18px",
    height="18px",
    border_radius="5px",
    border="1px solid var(--color-border)",
    background_color=Color(var="--color-surface"),
    appearance="none",
    cursor="pointer",
    flex_shrink="0",
    transition=Transition(duration="0.15s", timing="ease"),
)

_GLASS_BOX = _BOX.model_copy(
    update={
        "background_color": Color(var="--color-surface-glass-bg"),
        "backdrop_filter": "blur(8px)",
    }
)

# White check mark as a data-URI SVG, shown when checked.
_CHECK_SVG = (
    "<svg xmlns='http://www.w3.org/2000/svg' width='12' height='12' "
    "viewBox='0 0 24 24' fill='none' stroke='white' stroke-width='3' "
    "stroke-linecap='round' stroke-linejoin='round'>"
    "<polyline points='20 6 9 17 4 12'/></svg>"
)
_CHECK_MARK = f'url("data:image/svg+xml,{urllib.parse.quote(_CHECK_SVG)}")'

_CHECKED = _BOX.model_copy(
    update={
        "background_color": Color(var="--color-accent"),
        "background_image": _CHECK_MARK,
        "background_size": "12px 12px",
        "background_position": "center",
        "background_repeat": "no-repeat",
    }
)


class Checkbox(Component):
    #: Event types wired internally (via _bind / custom handlers) —
    #: Component.on() must not wire these again.
    _bound_events: frozenset[str] = frozenset({"change", "focus", "blur"})

    """A labelled checkbox with internal ``checked`` state.

    - ``checkbox.checked`` reads / sets state (immediate DOM write,
      no callback)
    - ``on_change(fn)`` fires on user toggles with the new value
    - ``glass=True`` gives the box a frosted, translucent surface
    """

    def __init__(self, label: str = "", *, checked: bool = False, glass: bool = False, disabled: bool = False) -> None:
        super().__init__()
        self._checked = checked
        self._disabled = disabled
        self._glass = glass
        self._focused = False

        self._input = _InputElem(type="checkbox", checked=checked, disabled=disabled)
        self._label_span = Span(container=[label])
        self._root = _LabelElem(styles=_ROW, container=[self._input, self._label_span])

        self._apply_box_style()
        self._bind(self._input, "change")
        self._bind(self._input, "focus")
        self._bind(self._input, "blur")

    # ---- state ----

    @property
    def checked(self) -> bool:
        return self._checked

    @checked.setter
    def checked(self, value: bool) -> None:
        self._checked = value
        self._input.checked = value  # immediate write; no callback
        self._apply_box_style()

    @property
    def label(self) -> str:
        return str(self._label_span.container[0]) if self._label_span.container else ""

    @label.setter
    def label(self, value: str) -> None:
        self._label_span.container = [value]

    @property
    def disabled(self) -> bool:
        return self._disabled

    @disabled.setter
    def disabled(self, value: bool) -> None:
        self._disabled = value
        self._input.disabled = value
        self._root.styles.opacity = 0.5 if value else None

    # ---- internals ----

    def _apply_box_style(self) -> None:
        """Sync the visible box style with the checked state."""
        if self._checked:
            base = _GLASS_BOX if self._glass else _BOX
            styles = base.model_copy(
                update={
                    "background_color": (
                        Color(var="--color-accent-glass-bg") if self._glass else Color(var="--color-accent")
                    ),
                    "background_image": _CHECK_MARK,
                    "background_size": "12px 12px",
                    "background_position": "center",
                    "background_repeat": "no-repeat",
                }
            )
        else:
            styles = (_GLASS_BOX if self._glass else _BOX).model_copy()
        if self._focused:
            # Colour-matched focus ring (the box has appearance:none —
            # no native focus indicator to fall back on).
            styles = styles.model_copy(update={"box_shadow": Theme.focus_glow("accent")})
        self._input.styles = styles

    # ---- events ----

    async def _on_event(self, event_type: str, event: DomEvent) -> None:
        if event_type == "change":
            self._checked = bool(event.value)
            self._input.checked = self._checked
            self._apply_box_style()
        elif event_type == "focus":
            self._focused = True
            self._apply_box_style()
        elif event_type == "blur":
            self._focused = False
            self._apply_box_style()
        await self._dispatch(event_type, event)
