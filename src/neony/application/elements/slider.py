"""Slider component — a range input with a custom animated fill track.

WebKit only restyles a range's track/thumb through ``::-webkit-*``
pseudo-elements (unrepresentable in this pipeline), so the visible
track, fill and thumb are drawn here: a rounded track with an accent
fill that transitions on programmatic value changes and follows the
thumb instantly while dragging.  The native range input sits on top
transparently — it owns focus, keyboard and drag behaviour.
"""

from __future__ import annotations

import asyncio
from typing import Literal

from neony.application.theme import Theme, stub
from neony.dom import Border, BoxShadow, Div, DOMElement, DomEvent, Shadow, Span, Styles, Transform, Transition, pct
from neony.dom import Input as _InputElem
from neony.dom import Label as _LabelElem

from .base import Component, ReactiveText, _mount_text

_ROW = Styles(display="flex", flex_direction="column", gap="6px", width="100%")

_LABEL = Styles(font_size="14px", color=stub.text_secondary)

# The thumb (8px radius) travels the track's full width, so the track
# is inset by 8px each side — at 0%/100% the thumb centres exactly on
# the track ends.
_THUMB_RADIUS = "8px"

_WRAP = Styles(position="relative", width="100%", height="22px")

_TRACK = Styles(
    position="absolute",
    top="50%",
    transform=Transform.translate(y="-50%"),
    left=_THUMB_RADIUS,
    right=_THUMB_RADIUS,
    height="6px",
    border_radius="999px",
    background_color=stub.surface_raised,
    overflow="hidden",
)

_FILL = Styles(
    height="100%",
    width="0%",
    border_radius="999px",
    background_color=stub.accent,
    transition=Transition(property="width", duration="0.2s", timing="ease"),
)

_THUMB = Styles(
    position="absolute",
    top="50%",
    left="0%",
    transform=Transform.translate(x="-50%", y="-50%"),  # centres the knob on the value point
    width="16px",
    height="16px",
    border_radius="50%",
    background_color=stub.surface_raised,
    border=Border(width="2px", color=stub.accent),
    box_shadow=BoxShadow(layers=[Shadow(x=0, y=2, blur=6, color=stub.shadow)]),
    transition=Transition(property="left", duration="0.2s", timing="ease"),
)

# The native control on top: invisible but interactive.  `margin: 0` —
# range inputs carry UA default margins that would offset the hit area.
_INPUT = Styles(
    position="absolute",
    top="0",
    left="0",
    width="100%",
    height="100%",
    opacity="0",
    margin="0",
    cursor="pointer",
)


def _clamp(value: float | int, lo: float | int, hi: float | int) -> float:
    """Clamp *value* to ``[lo, hi]`` (always a float) — module-level
    because ``min`` / ``max`` are constructor parameters here and
    shadow the builtins.  The parameters accept ints: component
    constructors store raw user arguments, which are commonly whole
    numbers, and the serialized value must still read ``"10.0"``."""
    return float(lo if value < lo else hi if value > hi else value)


class Slider(Component):
    #: Wired internally.  `input` = continuous drag, `change` = release.
    _bound_events: frozenset[str] = frozenset({"input", "change", "keydown", "focus", "blur"})

    #: bind_value user channel — drags deliver float values.
    _value_event: str | None = "input"

    """A draggable value selector with an animated fill track.

    - ``slider.value`` reads / sets the value (clamped to
      ``[min, max]``; programmatic writes glide the fill over 0.2s)
    - ``step="any"`` makes the slider stepless (continuous floats)
    - PageUp/PageDown move by a page step (10x step, or 10% of the
      range when stepless) — the native range input has this reversed
      (WebKit spec quirk), so the component corrects it
    - ``on_input(fn)`` fires continuously while dragging
    - ``on_change(fn)`` fires once when the drag is released
    """

    def __init__(
        self,
        label: ReactiveText = "",
        *,
        min: float = 0.0,
        max: float = 100.0,
        step: float | Literal["any"] = 1.0,
        value: float = 0.0,
        disabled: bool = False,
    ) -> None:
        super().__init__()
        if isinstance(step, (int, float)) and step <= 0:
            step = 1.0  # step=0 is invalid HTML; WebKit clamps it to 1 anyway
        self._label: ReactiveText = label
        self._min = min
        self._max = max
        self._step = step
        self._value = _clamp(value, min, max)
        self._disabled = disabled
        self._focused = False
        # Set by PageUp/PageDown keydown; the input event that follows
        # consumes it (see _on_keydown).
        self._page_target: float | None = None

        self._input = _InputElem(
            type="range", min=min, max=max, step=step, value=str(self._value), disabled=disabled, styles=_INPUT
        )
        self._fill = Div(styles=_FILL)
        self._thumb = Div(styles=_THUMB)
        self._track = Div(styles=_TRACK, container=[self._fill])
        self._wrapper = Div(styles=_WRAP, container=[self._track, self._thumb, self._input])

        # A reactive label (Signal/Computed) is always shown; a plain
        # string only when non-empty.
        show_label = bool(label) or not isinstance(label, str)
        self._label_span = Span(container=[], styles=_LABEL)
        if show_label:
            _mount_text(self._label_span, label)
        parts: list[DOMElement | str] = [self._wrapper]
        if show_label:
            parts.insert(0, self._label_span)
        self._root = _LabelElem(styles=_ROW, container=parts)

        self._apply_fill(animated=False)
        self._bind(self._input, "input")
        self._bind(self._input, "change")
        self._bind(self._input, "keydown")
        self._bind(self._input, "focus")
        self._bind(self._input, "blur")

    # ---- state ----

    @property
    def value(self) -> float:
        return self._value

    @value.setter
    def value(self, value: float) -> None:
        self._value = _clamp(value, self._min, self._max)
        self._input.value = str(self._value)  # immediate write; no callback
        self._apply_fill(animated=True)
        self._mirror_value(self._value)

    @property
    def label(self) -> str:
        if isinstance(self._label, str):
            return self._label
        return self._label()

    @label.setter
    def label(self, value: str) -> None:
        self._label = value
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

    def _apply_fill(self, animated: bool) -> None:
        """Sync the fill width + thumb position with the current value.

        *animated* is False while dragging (the fill must track the
        thumb with zero lag — a transition would trail one frame
        behind every input event) and True on programmatic sets (the
        fill glides to the new position).
        """
        span = self._max - self._min
        ratio = 0.0 if span <= 0 else (self._value - self._min) / span * 100.0
        width = pct(f"{ratio:.2f}")
        fill_style = _FILL.model_copy(update={"width": width})
        thumb_style = _THUMB.model_copy(update={"left": width})
        if not animated:
            fill_style = fill_style.model_copy(update={"transition": None})
            thumb_style = thumb_style.model_copy(update={"transition": None})
        if self._focused:
            # The native input is invisible — the focus ring lives on
            # the visible knob.
            thumb_style = thumb_style.model_copy(update={"box_shadow": Theme.focus_glow("accent")})
        self._fill.styles = fill_style
        self._thumb.styles = thumb_style

    # ---- events ----

    async def _on_event(self, event_type: str, event: DomEvent) -> None:
        if event_type in ("input", "change"):
            if self._page_target is not None:
                # A PageUp/PageDown keydown corrected the native range's
                # reversed page direction — take our target instead of
                # the native's value and write it back so the hidden
                # input's position stays in sync for the next drag.
                self._value = self._page_target
                self._page_target = None
                self._input.value = str(self._value)
            else:
                # Record-only on `input` (mirrors Input's loop guard);
                # `change` carries the same value on release.
                self._value = float(event.value)
            event.value = self._value
            self._apply_fill(animated=False)
        elif event_type == "keydown":
            await self._on_keydown(event)
        elif event_type == "focus":
            self._focused = True
            self._apply_fill(animated=False)
        elif event_type == "blur":
            self._focused = False
            self._apply_fill(animated=False)
        await self._dispatch(event_type, event)

    async def _on_keydown(self, event: DomEvent) -> None:
        if event.value not in ("PageUp", "PageDown"):
            return
        # The HTML spec makes the native range move PageUp DOWN and
        # PageDown UP (opposite of intuition, and of every other
        # control); we cannot preventDefault from Python, so schedule
        # the corrected value and let the input event that follows
        # consume it.
        page = 10.0 * self._step if isinstance(self._step, (int, float)) else (self._max - self._min) / 10.0
        delta = page if event.value == "PageUp" else -page
        self._page_target = _clamp(self._value + delta, self._min, self._max)
        # At the range ends the native move fires no input event — drop
        # the stale target shortly after, or the next drag would snap.
        asyncio.get_running_loop().call_later(0.5, self._clear_page_target)

    def _clear_page_target(self) -> None:
        self._page_target = None
