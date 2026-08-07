"""ComboBox component — editable text with a themed suggestion popup.

The native ``<datalist>`` suggestion popup is rendered by the OS/UI
process and cannot be themed, so the suggestions are drawn here: a
glass panel of native ``<button>`` rows anchored below the input,
filtered by prefix as you type.

Keyboard: ArrowDown/Up moves the highlighted suggestion, Enter picks
it, Escape closes, click-away closes via the engine's synthetic
``outsideclick`` event.  Value semantics match the Input component —
``input`` events record state only (no DOM write-back), ``change``
fires on a pick or on blur.
"""

from __future__ import annotations

from collections.abc import Sequence

from neony.application.theme import Theme
from neony.dom import Animation, Color, Div, DomEvent, Span, Styles, Transition
from neony.dom import Button as _ButtonElem
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

_FIELD = Styles(
    width="100%",
    padding="10px 14px",
    border_radius="8px",
    border="1px solid var(--color-border)",
    background_color=Color(var="--color-surface"),
    color=Color(var="--color-text-primary"),
    font_size="15px",
    outline="none",
    transition=Transition(property="border-color", duration="0.15s", timing="ease"),
)

_GLASS_FIELD = _FIELD.model_copy(
    update={
        "background_color": Color(var="--color-surface-glass-bg"),
        "backdrop_filter": "blur(8px)",
        "border": f"1px solid {Theme.glass_border('neutral')}",
    }
)

_WRAP = Styles(position="relative", flex_grow="1")

_PANEL = Styles(
    position="absolute",
    top="calc(100% + 6px)",
    left="0",
    right="0",
    z_index="500",
    display="none",
    flex_direction="column",
    padding="6px",
    gap="2px",
    border_radius="8px",
    border="1px solid var(--color-border-glass)",
    background_color=Color(var="--color-surface-glass-bg"),
    backdrop_filter="blur(20px) saturate(1.2)",
    box_shadow="0 8px 32px var(--color-shadow)",
)
# Entrance animation replays on every open (display: none → flex swaps
# the animation value, Tabs precedent).
_PANEL_OPEN = _PANEL.model_copy(
    update={
        "display": "flex",
        "animation": Animation(name="neony-rise-in", duration="0.2s", timing="ease-out"),
    }
)

_OPTION = Styles(
    display="flex",
    align_items="center",
    padding="8px 10px",
    border_radius="6px",
    border="none",
    background_color=Color(name="transparent"),
    color=Color(var="--color-text-primary"),
    font_size="14px",
    text_align="left",
    cursor="pointer",
    transition=Transition(duration="0.15s", timing="ease"),
)
_OPTION_ACTIVE = _OPTION.model_copy(update={"background_color": Color(var="--color-accent-glass-bg")})
_OPTION_HOVER = _OPTION.model_copy(update={"background_color": Color(var="--color-surface-glass-bg")})


class ComboBox(Component):
    #: Wired internally (via _bind / custom handlers) — Component.on()
    #: must not wire these again.
    _bound_events: frozenset[str] = frozenset(
        {"change", "input", "keydown", "outsideclick", "mouseover", "mouseout", "focus", "blur"}
    )

    #: bind_value user channels — keystrokes (``input``) AND picks /
    #: blur-commits (``change``); picks dispatch ``change`` only, so a
    #: single-channel binding would miss them.
    _value_events: tuple[str, ...] = ("input", "change")

    """An editable text field with a themed suggestion popup.

    - ``combobox.value`` reads / sets the current text (immediate DOM
      write, no callback)
    - ``on_input(fn)`` fires for every keystroke (user-driven only)
    - ``on_change(fn)`` fires on a suggestion pick or blur
    - ``options`` is a settable list of suggestion strings
    """

    def __init__(
        self,
        label: str = "",
        *,
        options: Sequence[str] = (),
        value: str = "",
        placeholder: str = "",
        glass: bool = False,
        disabled: bool = False,
    ) -> None:
        super().__init__()
        self._options = list(options)
        self._value = value
        self._disabled = disabled
        self._active_index = -1
        self._hovered: set[int] = set()
        self._rows: list[_ButtonElem] = []
        self._row_by_key: dict[str, str] = {}
        self._open = False

        self._input = _InputElem(
            type="text",
            placeholder=placeholder,
            value=value,
            disabled=disabled,
            styles=_GLASS_FIELD if glass else _FIELD,
        )
        self._popup = Div(styles=_PANEL, container=[])
        self._wrapper = Div(styles=_WRAP, container=[self._input, self._popup])
        # Keydowns from the input bubble up here.
        self._wrapper.bubble_events = True
        self._label_span = Span(container=[label])
        self._root = _LabelElem(styles=_ROW, container=[self._wrapper, self._label_span])

        self._bind(self._input, "input")
        self._bind(self._input, "change")
        self._bind(self._input, "focus")
        self._bind(self._input, "blur")
        self._bind(self._wrapper, "keydown")
        self._bind(self._wrapper, "outsideclick")

    # ---- state ----

    @property
    def value(self) -> str:
        return self._value

    @value.setter
    def value(self, value: str) -> None:
        self._value = value
        self._input.value = value  # immediate write; no callback

    @property
    def options(self) -> list[str]:
        return list(self._options)

    @options.setter
    def options(self, options: Sequence[str]) -> None:
        self._options = list(options)
        if self._open:
            self._rebuild_rows()

    @property
    def disabled(self) -> bool:
        return self._disabled

    @disabled.setter
    def disabled(self, value: bool) -> None:
        self._disabled = value
        self._input.disabled = value
        self._input.styles.opacity = 0.5 if value else None
        if value:
            self._close()

    # ---- internals ----

    def _matches(self) -> list[str]:
        query = self._value.strip().lower()
        return [o for o in self._options if o.lower().startswith(query)] if query else list(self._options)

    def _rebuild_rows(self) -> None:
        """Filter options by the current text and rebuild the popup.

        The highlight survives the rebuild (clamped to the new list) —
        resetting it on every rebuild would make the arrow keys step
        only between the first two items."""
        self._popup.container.clear()
        self._rows.clear()
        self._row_by_key.clear()
        self._hovered.clear()
        for opt in self._matches():
            row = _ButtonElem(type="button", container=[opt], styles=_OPTION, args={"role": "option"})
            self._rows.append(row)
            self._row_by_key[row.key] = opt
            self._bind(row, "click")
            self._bind(row, "mouseover")
            self._bind(row, "mouseout")
            self._popup.container.append(row)
        if not self._rows:
            self._active_index = -1
        elif self._active_index >= len(self._rows):
            self._active_index = len(self._rows) - 1
        elif self._active_index < 0:
            # The first match is the "accept this suggestion" default.
            self._active_index = 0

    def _apply_option_styles(self, index: int) -> None:
        if index == self._active_index:
            self._rows[index].styles = _OPTION_ACTIVE
        elif index in self._hovered:
            self._rows[index].styles = _OPTION_HOVER
        else:
            self._rows[index].styles = _OPTION

    def _open_popup(self) -> None:
        if self._open or self._disabled or not self._rows:
            return
        self._open = True
        self._popup.styles = _PANEL_OPEN
        self._wrapper.args = {**self._wrapper.args, "data-neony-outside": "true"}

    def _close(self) -> None:
        if not self._open:
            return
        self._open = False
        self._popup.styles = _PANEL
        self._wrapper.args = {k: v for k, v in self._wrapper.args.items() if k != "data-neony-outside"}

    def _move_active(self, delta: int) -> None:
        """Move the highlight by *delta*, clamped at the ends — no
        wrap-around (wrapping an auto-complete list loses your place;
        ArrowUp must always be able to return to the first item)."""
        if not self._rows:
            return
        self._active_index = max(0, min(len(self._rows) - 1, self._active_index + delta))
        for i in range(len(self._rows)):
            self._apply_option_styles(i)

    async def _pick(self, value: str, event: DomEvent | None) -> None:
        self.value = value
        self._close()
        if event is not None:
            event.value = value
            await self._dispatch("change", event)

    # ---- events ----

    async def _on_event(self, event_type: str, event: DomEvent) -> None:
        if event_type == "input":
            # Record state only — writing the value back would fire
            # another `input` event in WebKitGTK (infinite loop).
            self._value = str(event.value or "")
            self._rebuild_rows()
            if self._rows:
                self._open_popup()
            else:
                self._close()
        elif event_type == "change":
            # A blur right after Tab/Enter auto-complete fires `change`
            # with the PRE-pick value — the pick's write-back hasn't
            # reached the browser yet (Tab moves focus before Python
            # runs).  `_value` already holds the live text from `input`
            # events, so a mismatching change is stale: ignore it, or it
            # would clobber the picked value and fire a wrong callback
            # (e.g. a readout stuck on the pre-pick text).
            if str(event.value or "") == self._value:
                await self._dispatch("change", event)
            return  # stale or not — never fall through to the trailing dispatch
        elif event_type == "click":
            if event.key in self._row_by_key:
                await self._pick(self._row_by_key[event.key], event)
        elif event_type == "mouseover":
            index = self._index_of_row(event.key)
            if index >= 0:
                self._hovered.add(index)
                self._apply_option_styles(index)
        elif event_type == "mouseout":
            index = self._index_of_row(event.key)
            if index >= 0:
                self._hovered.discard(index)
                self._apply_option_styles(index)
        elif event_type == "keydown":
            await self._on_keydown(event)
        elif event_type == "outsideclick":
            self._close()
        elif event_type == "focus":
            # Focus ring replaces the native outline; ``model_copy`` —
            # _FIELD is a shared constant.
            self._input.styles = self._input.styles.model_copy(update={"box_shadow": Theme.focus_glow("accent")})
            # Opening on focus makes the suggestions reachable with a
            # single click — no keystroke required.
            self._rebuild_rows()
            if self._rows:
                self._open_popup()
        elif event_type == "blur":
            self._input.styles = self._input.styles.model_copy(update={"box_shadow": None})
        await self._dispatch(event_type, event)

    def _index_of_row(self, key: str) -> int:
        for i, row in enumerate(self._rows):
            if row.key == key:
                return i
        return -1

    async def _on_keydown(self, event: DomEvent) -> None:
        key = event.value
        if key in ("ArrowDown", "ArrowUp"):
            self._rebuild_rows()  # rows must match the current text
            if self._rows:
                self._open_popup()
                self._move_active(1 if key == "ArrowDown" else -1)
        elif key in ("PageDown", "PageUp"):
            # Page keys pick the first/last suggestion in one keypress —
            # PageUp commits the first item without touching the arrows.
            self._rebuild_rows()
            if self._rows:
                target = self._rows[-1] if key == "PageDown" else self._rows[0]
                await self._pick(self._row_by_key[target.key], event)
        elif key in ("Enter", "Tab"):
            # Auto-complete: Tab or Enter accepts the highlighted
            # suggestion, refiltered against the CURRENT text — works
            # even with the popup closed (edited text, click-away), so
            # the completion always follows what was typed.
            self._rebuild_rows()
            if 0 <= self._active_index < len(self._rows):
                await self._pick(self._row_by_key[self._rows[self._active_index].key], event)
        elif key == "Escape":
            self._close()
