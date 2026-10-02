"""Text input component — stateful, themed, source-aware events."""

from __future__ import annotations

import json
from typing import Literal

from neony.application.theme import Theme, stub
from neony.dom import Border, Color, Div, DOMElement, DomEvent, Filter, Span, Styles, Transition
from neony.dom import Button as _ButtonElem
from neony.dom import Input as _InputElem

from .base import Component, ReactiveText
from .icon import Icon

InputAdornment = str | Icon | DOMElement | Component

_FIELD = Styles(
    width="100%",
    display="flex",
    align_items="center",
    gap="8px",
    padding="10px 14px",
    border_radius="8px",
    border=Border(width="1px", color=stub.border),
    background_color=stub.surface,
    color=stub.text_primary,
    font_size="15px",
    outline="none",
    transition=Transition(property="border-color", duration="0.15s", timing="ease"),
)

_GLASS_FIELD = _FIELD.model_copy(
    update={
        "background_color": stub.surface_glass_bg,
        "backdrop_filter": Filter(blur="8px"),
        "border": f"1px solid {Theme.glass_border('neutral')}",
    }
)

_INPUT = Styles(
    width="100%",
    min_width="0",
    flex_grow="1",
    padding="0",
    border="none",
    outline="none",
    background_color=Color(name="transparent"),
    color=Color(name="inherit"),
    font_size="inherit",
)

_ADORNMENT = Styles(color=stub.text_secondary, font_size="13px", flex_shrink="0")
_ACTION = Styles(
    display="inline-flex",
    align_items="center",
    justify_content="center",
    width="20px",
    height="20px",
    padding="0",
    border="none",
    background_color=Color(name="transparent"),
    color=stub.text_secondary,
    cursor="pointer",
    flex_shrink="0",
)


class Input(Component):
    #: Event types wired internally (via _bind / custom handlers) —
    #: Component.on() must not wire these again.
    _bound_events: frozenset[str] = frozenset({"input", "change", "focus", "blur", "keydown"})

    #: bind_value user channel — live keystrokes.
    _value_event: str | None = "input"

    """Single-line text field with internal value state.

    - ``input.value`` reads / sets the current text (immediate DOM write)
    - ``on_input(fn)`` fires for every keystroke (user-driven only)
    - ``on_change(fn)`` fires when the field loses focus after edits
    - ``on_submit(fn)`` fires on Enter outside IME composition
    - ``prefix`` / ``suffix`` accept text, Icon, Component or DOMElement
    - ``clearable=True`` adds a clear action; password fields can reveal
    """

    def __init__(
        self,
        placeholder: ReactiveText = "",
        *,
        value: str = "",
        type: Literal["text", "password", "email", "number", "search", "tel", "url"] = "text",
        glass: bool = False,
        disabled: bool = False,
        maxlength: int | None = None,
        prefix: InputAdornment | None = None,
        suffix: InputAdornment | None = None,
        clearable: bool = False,
        reveal_password: bool = False,
    ) -> None:
        super().__init__()
        self._placeholder: ReactiveText = placeholder
        self._value = value
        self._disabled = disabled
        self._prefix = prefix
        self._suffix = suffix
        self._clearable = clearable
        self._reveal_password = reveal_password and type == "password"
        self._password_visible = False

        self._input = _InputElem(
            type=type,
            placeholder=placeholder if isinstance(placeholder, str) else None,
            value=value,
            maxlength=maxlength,
            disabled=disabled,
            styles=_INPUT,
        )
        if not isinstance(placeholder, str):
            self._input.bind_attr(placeholder, "placeholder")

        self._prefix_slot = self._render_adornment(prefix)
        self._suffix_slot = self._render_adornment(suffix)
        self._clear_button = self._make_action("cancel", "Clear") if clearable else None
        self._reveal_button = self._make_action("visibility", "Show password") if self._reveal_password else None

        self._wrapper = Div(styles=_GLASS_FIELD if glass else _FIELD, container=[])
        self._wrapper.bubble_events = True
        self._root = self._wrapper
        self._rebuild_content()
        self._sync_actions()

        self._bind(self._input, "input")
        self._bind(self._input, "change")
        self._bind(self._input, "focus")
        self._bind(self._input, "blur")
        self._bind(self._input, "keydown")
        if self._clear_button is not None:
            self._clear_button.on("click", self._on_clear)
        if self._reveal_button is not None:
            self._reveal_button.on("click", self._on_reveal)

    @staticmethod
    def _render_adornment(value: InputAdornment | None) -> DOMElement | str | None:
        if value is None:
            return None
        if isinstance(value, Component):
            return value.build()
        if isinstance(value, Icon):
            return value.render("16px")
        if isinstance(value, str):
            return Span(container=[value], styles=_ADORNMENT)
        return value

    @staticmethod
    def _make_action(icon: str, label: str) -> _ButtonElem:
        return _ButtonElem(
            type="button",
            container=[Icon._font(icon).render("16px")],
            styles=_ACTION,
            args={"aria-label": label},
        )

    def _rebuild_content(self) -> None:
        parts: list[DOMElement | str] = []
        if self._prefix_slot is not None:
            parts.append(self._prefix_slot)
        parts.append(self._input)
        if self._clear_button is not None:
            parts.append(self._clear_button)
        if self._reveal_button is not None:
            parts.append(self._reveal_button)
        if self._suffix_slot is not None:
            parts.append(self._suffix_slot)
        self._wrapper.container = parts

    def _sync_actions(self) -> None:
        if self._clear_button is not None:
            self._clear_button.styles = _ACTION.model_copy(
                update={"display": "inline-flex" if self._value and not self._disabled else "none"}
            )
            self._clear_button.disabled = self._disabled
        if self._reveal_button is not None:
            self._reveal_button.disabled = self._disabled

    # ---- state ----

    @property
    def value(self) -> str:
        return self._value

    @value.setter
    def value(self, value: str) -> None:
        self._value = value
        self._input.value = value  # immediate write; no callback
        self._sync_actions()
        self._mirror_value(value)

    @property
    def placeholder(self) -> str:
        if isinstance(self._placeholder, str):
            return self._placeholder
        return self._placeholder()

    @placeholder.setter
    def placeholder(self, value: str) -> None:
        self._placeholder = value
        self._input.placeholder = value

    @property
    def prefix(self) -> InputAdornment | None:
        return self._prefix

    @prefix.setter
    def prefix(self, value: InputAdornment | None) -> None:
        self._prefix = value
        self._prefix_slot = self._render_adornment(value)
        self._rebuild_content()

    @property
    def suffix(self) -> InputAdornment | None:
        return self._suffix

    @suffix.setter
    def suffix(self, value: InputAdornment | None) -> None:
        self._suffix = value
        self._suffix_slot = self._render_adornment(value)
        self._rebuild_content()

    @property
    def disabled(self) -> bool:
        return self._disabled

    @disabled.setter
    def disabled(self, value: bool) -> None:
        self._disabled = value
        self._input.disabled = value
        self._wrapper.styles = self._wrapper.styles.model_copy(update={"opacity": 0.5 if value else None})
        self._sync_actions()

    @property
    def control_element(self) -> DOMElement:
        """The native input that owns value, focus and form semantics."""
        return self._input

    # ---- events ----

    async def _on_clear(self, event: DomEvent) -> None:
        event.source = "user"
        event.value = ""
        self.value = ""
        await self._dispatch("input", event)
        await self._dispatch("change", event)

    async def _on_reveal(self, event: DomEvent) -> None:
        event.source = "user"
        self._password_visible = not self._password_visible
        self._input.type = "text" if self._password_visible else "password"
        if self._reveal_button is not None:
            icon = "visibility_off" if self._password_visible else "visibility"
            self._reveal_button.container = [Icon._font(icon).render("16px")]
            self._reveal_button.args = {
                **self._reveal_button.args,
                "aria-label": "Hide password" if self._password_visible else "Show password",
            }
        self._schedule_js(
            "(() => { const el = window.neony && window.neony.engine && "
            f"window.neony.engine.registry.get({json.dumps(self._input.key)}); "
            "if (el && typeof el.focus === 'function') el.focus(); })()"
        )
        await self._dispatch("click", event)

    async def _on_event(self, event_type: str, event: DomEvent) -> None:
        if event_type == "input":
            # Record state only — writing the value back would fire
            # another `input` event in WebKitGTK (infinite loop).
            self._value = str(event.value or "")
            self._sync_actions()
        elif event_type == "focus":
            self._wrapper.styles = self._wrapper.styles.model_copy(update={"box_shadow": Theme.focus_glow("accent")})
        elif event_type == "blur":
            self._wrapper.styles = self._wrapper.styles.model_copy(update={"box_shadow": None})
        elif event_type == "keydown" and event.value == "Enter" and not event.is_composing:
            event.value = self._value
            await self._dispatch("submit", event)
        await self._dispatch(event_type, event)

    def on_submit(self, fn) -> Input:
        return self.on("submit", fn)
