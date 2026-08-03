"""Text input component — stateful, themed, source-aware events."""

from __future__ import annotations

from typing import Literal

from neony.application.theme import Theme
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

_GLASS_FIELD = _FIELD.model_copy(
    update={
        "background_color": Color(var="--color-surface-glass-bg"),
        "backdrop_filter": "blur(8px)",
        "border": f"1px solid {Theme.glass_border('neutral')}",
    }
)


class Input(Component):
    """Single-line text field with internal value state.

    - ``input.value`` reads / sets the current text (immediate DOM write)
    - ``on_input(fn)`` fires for every keystroke (user-driven only)
    - ``on_change(fn)`` fires when the field loses focus after edits
    - ``glass=True`` gives the field a frosted, translucent surface
    """

    def __init__(
        self,
        placeholder: str = "",
        *,
        value: str = "",
        type: Literal["text", "password", "email", "number", "search", "tel", "url"] = "text",
        glass: bool = False,
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
            styles=_GLASS_FIELD if glass else _FIELD,
        )
        self._root = self._input

        self._bind(self._input, "input")
        self._bind(self._input, "change")
        self._bind(self._input, "focus")
        self._bind(self._input, "blur")

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
        elif event_type == "focus":
            # Colour-matched focus ring replaces the removed native
            # outline.  ``model_copy`` — _FIELD is a shared module
            # constant and must not be mutated in place.
            self._input.styles = self._input.styles.model_copy(
                update={"box_shadow": Theme.focus_glow("accent")}
            )
        elif event_type == "blur":
            self._input.styles = self._input.styles.model_copy(update={"box_shadow": None})
        await self._dispatch(event_type, event)
