"""Checkbox component — stateful, themed, chainable events."""

from __future__ import annotations

from neony.dom import Color, DomEvent, Span, Styles
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


class Checkbox(Component):
    """A labelled checkbox with internal ``checked`` state.

    - ``checkbox.checked`` reads / sets state (immediate DOM write,
      no callback)
    - ``on_change(fn)`` fires on user toggles with the new value
    """

    def __init__(self, label: str = "", *, checked: bool = False, disabled: bool = False) -> None:
        super().__init__()
        self._checked = checked
        self._disabled = disabled

        self._input = _InputElem(type="checkbox", checked=checked, disabled=disabled)
        self._label_span = Span(container=[label])
        self._root = _LabelElem(styles=_ROW, container=[self._input, self._label_span])

        self._bind(self._input, "change")

    # ---- state ----

    @property
    def checked(self) -> bool:
        return self._checked

    @checked.setter
    def checked(self, value: bool) -> None:
        self._checked = value
        self._input.checked = value  # immediate write; no callback

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

    # ---- events ----

    async def _on_event(self, event_type: str, event: DomEvent) -> None:
        if event_type == "change":
            self._checked = bool(event.value)
            self._input.checked = self._checked
        await self._dispatch(event_type, event)
