"""Progress component — a themed bar with an animated fill.

The fill is a child of a rounded, overflow-hidden track; its width
transitions over 0.3s on value changes, so updates glide instead of
snapping.  ``indeterminate=True`` swaps in a sliding sweep animation
(the built-in ``neony-indeterminate`` keyframe, injected into every
window with the theme).  ARIA role/attributes keep the custom bar
accessible.
"""

from __future__ import annotations

from neony.application.theme import stub
from neony.dom import Animation, Div, DOMElement, Span, Styles, Transition, pct

from .base import Component

_WRAP = Styles(display="flex", flex_direction="column", gap="6px", width="100%")

_LABEL = Styles(font_size="14px", color=stub.text_secondary)

_TRACK = Styles(
    width="100%",
    height="8px",
    border_radius="999px",
    background_color=stub.surface_raised,
    overflow="hidden",
)

_FILL = Styles(
    height="100%",
    width="0%",
    border_radius="999px",
    background_color=stub.accent,
    transition=Transition(property="width", duration="0.3s", timing="ease"),
)

# Indeterminate: a 40%-wide fill sweeping left→right across the
# overflow-hidden track (see the built-in neony-indeterminate keyframe).
_INDETERMINATE_FILL = _FILL.model_copy(
    update={
        "width": "40%",
        "transition": None,
        "animation": Animation(
            name="neony-indeterminate",
            duration="1.2s",
            timing="ease-in-out",
            iteration_count="infinite",
        ),
    }
)


def _clamp(value: float | int, lo: float | int, hi: float | int) -> float:
    """Clamp *value* to ``[lo, hi]`` (always a float) — module-level
    because ``max`` is a constructor parameter here and shadows the
    builtin.  The parameters accept ints: component constructors store
    raw user arguments, which are commonly whole numbers, and the
    serialized value must still read ``"10.0"``."""
    return float(lo if value < lo else hi if value > hi else value)


class Progress(Component):
    #: No user events — on_* callbacks still work via lazy root wiring.
    _bound_events: frozenset[str] = frozenset()

    """A determinate or indeterminate progress bar with an animated
    fill.

    - ``progress.value`` reads / sets the current value (clamped to
      ``[0, max]``; the fill glides over 0.3s)
    - ``progress.indeterminate`` shows the sliding sweep animation
      (its ``value`` is ignored)
    """

    def __init__(self, label: str = "", *, value: float = 0.0, max: float = 100.0, indeterminate: bool = False) -> None:
        super().__init__()
        self._max = max
        self._indeterminate = indeterminate
        self._value = _clamp(value, 0.0, max)

        # ARIA mirrors the semantics a native <progress> would carry.
        args: dict[str, str] = {"role": "progressbar", "aria-valuemin": "0", "aria-valuemax": f"{max:g}"}
        if not indeterminate:
            args["aria-valuenow"] = f"{self._value:g}"
        self._fill = Div(
            styles=_INDETERMINATE_FILL if indeterminate else _FILL.model_copy(update={"width": self._pct()})
        )
        self._track = Div(styles=_TRACK, args=args, container=[self._fill])

        parts: list[DOMElement | str] = [self._track]
        if label:
            parts.insert(0, Span(container=[label], styles=_LABEL))
        self._root = Div(styles=_WRAP, container=parts)

    # ---- state ----

    @property
    def value(self) -> float:
        return self._value

    @value.setter
    def value(self, value: float) -> None:
        if self._indeterminate:
            return  # indeterminate bars have no value
        self._value = _clamp(value, 0.0, self._max)
        self._fill.styles = _FILL.model_copy(update={"width": self._pct()})  # immediate write; no callback
        self._track.args = {**self._track.args, "aria-valuenow": f"{self._value:g}"}

    @property
    def max(self) -> float:
        return self._max

    @max.setter
    def max(self, value: float) -> None:
        self._max = value
        self._track.args = {**self._track.args, "aria-valuemax": f"{value:g}"}

    @property
    def indeterminate(self) -> bool:
        return self._indeterminate

    # ---- internals ----

    def _pct(self) -> str:
        """The fill width for the current value (0% when max <= 0)."""
        ratio = 0.0 if self._max <= 0 else self._value / self._max * 100.0
        return pct(f"{ratio:.1f}")
