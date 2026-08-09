"""Switch component — a themed toggle built on a native checkbox.

The input IS the track: ``appearance: none`` strips the native box, and
the thumb is an SVG data-URI background whose ``currentColor`` fill
inherits the element's token-driven ``color`` (data-URI documents
cannot resolve ``var(--color-*)``, but ``currentColor`` works).
"""

from __future__ import annotations

import urllib.parse

from neony.application.theme import Theme, stub
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
    color=stub.text_primary,
)

_THUMB_SVG = (
    "<svg xmlns='http://www.w3.org/2000/svg' width='18' height='18' "
    "viewBox='0 0 18 18'><circle cx='9' cy='9' r='8' fill='currentColor' "
    "opacity='0.95'/></svg>"
)
_THUMB = f'url("data:image/svg+xml,{urllib.parse.quote(_THUMB_SVG)}")'

_TRACK = Styles(
    width="38px",
    height="22px",
    border_radius="999px",
    background_color=stub.surface_raised,
    background_image=_THUMB,
    background_size="18px 18px",
    background_position="2px center",
    background_repeat="no-repeat",
    appearance="none",
    cursor="pointer",
    flex_shrink="0",
    # Thumb fill (currentColor) — muted when off, white when on.
    color=stub.text_secondary,
    transition=Transition(duration="0.15s", timing="ease"),
)

_GLASS_TRACK = _TRACK.model_copy(
    update={
        "background_color": stub.surface_glass_bg,
        "backdrop_filter": "blur(8px)",
    }
)

_CHECKED_TRACK = _TRACK.model_copy(
    update={
        # 38 - 22 + 2 = 18 — the thumb sits flush against the right edge.
        "background_position": "18px center",
        "background_color": stub.accent,
        "color": Color(name="white"),
    }
)

_GLASS_CHECKED_TRACK = _CHECKED_TRACK.model_copy(
    update={
        "background_color": stub.accent_glass_bg,
        "backdrop_filter": "blur(8px)",
    }
)


class Switch(Component):
    #: Event types wired internally (via _bind / custom handlers) —
    #: Component.on() must not wire these again.
    _bound_events: frozenset[str] = frozenset({"change", "focus", "blur"})

    #: bind_value binds ``checked`` (there is no ``value``); the change
    #: event carries the new bool.
    _value_prop: str = "checked"
    _value_event: str | None = "change"

    """A labelled on/off switch with internal ``checked`` state.

    - ``switch.checked`` reads / sets state (immediate DOM write,
      no callback)
    - ``on_change(fn)`` fires on user toggles with the new bool
    - ``glass=True`` gives the track a frosted, translucent surface
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

        self._apply_track_style()
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
        self._apply_track_style()

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

    def _apply_track_style(self) -> None:
        """Sync the visible track with the checked state."""
        if self._checked:
            styles = (_GLASS_CHECKED_TRACK if self._glass else _CHECKED_TRACK).model_copy()
        else:
            styles = (_GLASS_TRACK if self._glass else _TRACK).model_copy()
        if self._focused:
            # Colour-matched focus ring (the track has appearance:none —
            # no native focus indicator to fall back on).
            styles = styles.model_copy(update={"box_shadow": Theme.focus_glow("accent")})
        self._input.styles = styles

    # ---- events ----

    async def _on_event(self, event_type: str, event: DomEvent) -> None:
        if event_type == "change":
            self._checked = bool(event.value)
            self._input.checked = self._checked
            self._apply_track_style()
        elif event_type == "focus":
            self._focused = True
            self._apply_track_style()
        elif event_type == "blur":
            self._focused = False
            self._apply_track_style()
        await self._dispatch(event_type, event)
