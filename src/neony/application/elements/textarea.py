"""Multiline text input component with source-aware state."""

from __future__ import annotations

from typing import Literal

from neony.application.theme import Theme, stub
from neony.dom import Border, DomEvent, Filter, Styles, Transition
from neony.dom import Textarea as _TextareaElem

from .base import Component, ReactiveText

_FIELD = Styles(
    width="100%",
    min_height="96px",
    padding="10px 14px",
    border_radius="8px",
    border=Border(width="1px", color=stub.border),
    background_color=stub.surface,
    color=stub.text_primary,
    font_family="inherit",
    font_size="15px",
    line_height="1.5",
    outline="none",
    box_sizing="border-box",
    resize="vertical",
    transition=Transition(property="border-color", duration="0.15s", timing="ease"),
)

_GLASS_FIELD = _FIELD.model_copy(
    update={
        "background_color": stub.surface_glass_bg,
        "backdrop_filter": Filter(blur="8px"),
        "border": f"1px solid {Theme.glass_border('neutral')}",
    }
)


class Textarea(Component):
    """Multiline text field with internal value state.

    - ``textarea.value`` reads / sets the current text
    - ``on_input(fn)`` fires for every edit
    - ``on_change(fn)`` fires when the field loses focus after edits
    - ``resize`` is ``"none"`` / ``"both"`` / ``"horizontal"`` /
      ``"vertical"``
    """

    _bound_events: frozenset[str] = frozenset({"input", "change", "focus", "blur"})
    _value_event: str | None = "input"

    def __init__(
        self,
        placeholder: ReactiveText = "",
        *,
        value: str = "",
        rows: int = 4,
        resize: Literal["none", "both", "horizontal", "vertical"] = "vertical",
        glass: bool = False,
        disabled: bool = False,
        maxlength: int | None = None,
    ) -> None:
        if rows <= 0:
            raise ValueError(f"Textarea: rows must be positive, got {rows!r}")
        if maxlength is not None and maxlength < 0:
            raise ValueError(f"Textarea: maxlength must be non-negative, got {maxlength!r}")
        super().__init__()
        self._placeholder: ReactiveText = placeholder
        self._value = value
        self._disabled = disabled

        styles = (_GLASS_FIELD if glass else _FIELD).model_copy(update={"resize": resize})
        self._textarea = _TextareaElem(
            placeholder=placeholder if isinstance(placeholder, str) else None,
            value=value,
            rows=rows,
            maxlength=maxlength,
            disabled=disabled,
            styles=styles,
            container=[] if value == "" else [value],
        )
        self._root = self._textarea
        if not isinstance(placeholder, str):
            self._textarea.bind_attr(placeholder, "placeholder")

        self._bind(self._textarea, "input")
        self._bind(self._textarea, "change")
        self._bind(self._textarea, "focus")
        self._bind(self._textarea, "blur")

    @property
    def value(self) -> str:
        return self._value

    @value.setter
    def value(self, value: str) -> None:
        self._value = value
        self._textarea.value = value
        self._textarea.container = [] if value == "" else [value]
        self._mirror_value(value)

    @property
    def placeholder(self) -> str:
        if isinstance(self._placeholder, str):
            return self._placeholder
        return self._placeholder()

    @placeholder.setter
    def placeholder(self, value: str) -> None:
        self._placeholder = value
        self._textarea.placeholder = value

    @property
    def disabled(self) -> bool:
        return self._disabled

    @disabled.setter
    def disabled(self, value: bool) -> None:
        self._disabled = value
        self._textarea.disabled = value
        self._textarea.styles.opacity = 0.5 if value else None

    async def _on_event(self, event_type: str, event: DomEvent) -> None:
        if event_type in ("input", "change"):
            self._value = str(event.value or "")
        elif event_type == "focus":
            self._textarea.styles = self._textarea.styles.model_copy(update={"box_shadow": Theme.focus_glow("accent")})
        elif event_type == "blur":
            self._textarea.styles = self._textarea.styles.model_copy(update={"box_shadow": None})
        await self._dispatch(event_type, event)
