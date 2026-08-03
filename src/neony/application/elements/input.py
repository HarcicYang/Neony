"""Text input component — stateful, themed, source-aware events."""

from __future__ import annotations

from typing import Literal

from neony.dom import Color, DomEvent, Styles
from neony.dom import Input as _InputElem

from .base import Component

_FIELD = Styles(
    width="100%",
    padding="10px 14px",
    border_radius="8px",
    border="1px solid var(--color-border)",
    background_color=Color(var="--color-surface"),
    color=Color(var="--color-text-primary"),
    font_size="15px",
    outline="none",
    transition="border-color 0.15s ease",
)


class Input(Component):
    """Single-line text field with internal value state.

    - ``input.value`` reads / sets the current text (immediate DOM write)
    - ``on_input(fn)`` fires for every keystroke (user-driven only)
    - ``on_change(fn)`` fires when the field loses focus after edits
    """

    def __init__(
        self,
        placeholder: str = "",
        *,
        value: str = "",
        type: Literal["text", "password", "email", "number", "search", "tel", "url"] = "text",
        disabled: bool = False,
        maxlength: int | None = None,
    ) -> None:
        super().__init__()
        self._value = value
        self._disabled = disabled

        self._input = _InputElem(
            type=type,
            placeholder=placeholder,
            value=value,
            maxlength=maxlength,
            disabled=disabled,
            styles=_FIELD,
        )
        self._root = self._input

        self._bind(self._input, "input")
        self._bind(self._input, "change")

    # ---- state ----

    @property
    def value(self) -> str:
        return self._value

    @value.setter
    def value(self, value: str) -> None:
        self._value = value
        self._input.value = value  # immediate write; no callback

    @property
    def disabled(self) -> bool:
        return self._disabled

    @disabled.setter
    def disabled(self, value: bool) -> None:
        self._disabled = value
        self._input.disabled = value
        self._input.styles.opacity = 0.5 if value else None

    # ---- events ----

    async def _on_event(self, event_type: str, event: DomEvent) -> None:
        if event_type == "input":
            # Record state only — the DOM already holds the typed value.
            # Writing it back would diff an UpdateAttrsPatch → JS
            # setAttribute("value") → WebKitGTK fires another input
            # event → infinite loop / frozen page.
            self._value = str(event.value or "")
        await self._dispatch(event_type, event)
