"""Select component — a themed dropdown with a custom popup.

WebKitGTK renders the native ``<select>`` popup in the UI process with
GTK widgets, where option ``background-color`` is ignored (WebKit bug
9846, open since 2006) — so the popup here is drawn by the component: a
glass panel of native ``<button>`` rows anchored below the trigger.

Keyboard: Enter/Space opens, ArrowDown/Up moves the highlighted row,
Enter picks it, Escape/Tab closes.  Click-away closes via the engine's
synthetic ``outsideclick`` event (``data-neony-outside`` marker).
"""

from __future__ import annotations

import urllib.parse
from collections.abc import Sequence

from neony.application.theme import Theme
from neony.dom import Animation, Color, Div, DomEvent, Span, Styles, Transition
from neony.dom import Button as _ButtonElem
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

_CHEVRON_SVG = (
    "<svg xmlns='http://www.w3.org/2000/svg' width='16' height='16' viewBox='0 0 16 16' "
    "fill='none' stroke='currentColor' stroke-width='2' stroke-linecap='round' "
    "stroke-linejoin='round'><path d='M4 6l4 4 4-4'/></svg>"
)
_CHEVRON_UP_SVG = _CHEVRON_SVG.replace("M4 6l4 4 4-4", "M4 10l4-4 4 4")
_CHEVRON = f'url("data:image/svg+xml,{urllib.parse.quote(_CHEVRON_SVG)}")'
_CHEVRON_UP = f'url("data:image/svg+xml,{urllib.parse.quote(_CHEVRON_UP_SVG)}")'

_TRIGGER = Styles(
    flex_grow="1",
    padding="10px 34px 10px 14px",  # right padding leaves room for the chevron
    border_radius="8px",
    border="1px solid var(--color-border)",
    background_color=Color(var="--color-surface"),
    color=Color(var="--color-text-primary"),
    font_size="15px",
    cursor="pointer",
    user_select="none",
    outline="none",
    background_image=_CHEVRON,
    background_size="16px 16px",
    background_position="right 12px center",
    background_repeat="no-repeat",
    transition=Transition(property="border-color", duration="0.15s", timing="ease"),
)

_GLASS_TRIGGER = _TRIGGER.model_copy(
    update={
        "background_color": Color(var="--color-surface-glass-bg"),
        "backdrop_filter": "blur(8px)",
        "border": f"1px solid {Theme.glass_border('neutral')}",
    }
)

_PLACEHOLDER_TEXT = Styles(color=Color(var="--color-text-secondary"))

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
    max_height="calc(100vh - 8px)",
    overflow="auto",
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
_OPTION_DISABLED = _OPTION.model_copy(update={"color": Color(var="--color-text-secondary"), "cursor": "default"})


class Select(Component):
    #: Wired internally (via _bind / custom handlers) — Component.on()
    #: must not wire these again.  ``change`` is dispatched manually.
    _bound_events: frozenset[str] = frozenset(
        {"change", "click", "keydown", "outsideclick", "mouseover", "mouseout", "focus", "blur"}
    )

    #: bind_value user channel — the manually dispatched selection.
    _value_event: str | None = "change"

    """A themed dropdown with a custom popup, internal ``value`` state.

    - ``select.value`` reads / sets the selected option's value
      (immediate DOM write, no callback)
    - ``on_change(fn)`` fires on user selections with the value string
    - ``glass=True`` gives the trigger a frosted, translucent surface
    - options are ``str`` (value == label) or ``(value, label)`` tuples
    """

    def __init__(
        self,
        label: str = "",
        *,
        options: Sequence[str | tuple[str, str]] = (),
        value: str | None = None,
        placeholder: str | None = None,
        glass: bool = False,
        disabled: bool = False,
    ) -> None:
        super().__init__()
        self._options: list[tuple[str, str]] = []
        self._label_by_value: dict[str, str] = {}
        self._rows: list[tuple[str | None, _ButtonElem]] = []
        self._row_by_key: dict[str, str | None] = {}
        self._hovered: set[int] = set()
        self._active_index = -1
        self._value: str | None = None
        self._disabled = disabled
        self._placeholder = placeholder
        self._focused = False
        self._open = False

        self._selected_span = Span(container=[""])
        self._trigger = Div(
            styles=_GLASS_TRIGGER if glass else _TRIGGER,
            args={"tabindex": "0", "role": "combobox", "aria-haspopup": "listbox", "aria-expanded": "false"},
            container=[self._selected_span],
        )
        self._popup = Div(styles=_PANEL, container=[])
        self._wrapper = Div(styles=_WRAP, container=[self._trigger, self._popup])
        # Keydowns from the trigger or a focused option bubble up here.
        self._wrapper.bubble_events = True
        self._label_span = Span(container=[label])
        self._root = _LabelElem(styles=_ROW, container=[self._wrapper, self._label_span])

        self._build_placeholder()
        for entry in options:
            self._add_option(entry)
        if value is not None:
            self.value = value
        else:
            self._sync_trigger()

        self._bind(self._trigger, "click")
        self._bind(self._trigger, "focus")
        self._bind(self._trigger, "blur")
        self._bind(self._wrapper, "keydown")
        self._bind(self._wrapper, "outsideclick")

    # ---- state ----

    @property
    def value(self) -> str | None:
        return self._value

    @value.setter
    def value(self, value: str | None) -> None:
        self._value = value
        self._active_index = self._index_of(value)
        self._sync_trigger()
        for i in range(len(self._rows)):
            self._apply_option_styles(i)

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
        self._root.styles.opacity = 0.5 if value else None
        if value:
            self._close()

    # ---- internals ----

    def _add_option(self, entry: str | tuple[str, str]) -> None:
        if isinstance(entry, tuple):
            value, label = entry
        else:
            value = label = entry
        self._options.append((value, label))
        self._label_by_value[value] = label
        self._popup.container.append(self._make_option(value, label))

    def _make_option(self, value: str | None, label: str, *, placeholder: bool = False) -> _ButtonElem:
        row = _ButtonElem(
            type="button",
            container=[label],
            styles=_OPTION_DISABLED if placeholder else _OPTION,
            args={"role": "option"} if not placeholder else {"role": "option", "disabled": ""},
        )
        self._rows.append((value, row))
        self._row_by_key[row.key] = value
        if not placeholder:
            self._bind(row, "click")
            self._bind(row, "mouseover")
            self._bind(row, "mouseout")
        return row

    def _build_placeholder(self) -> None:
        """Insert the placeholder option first (it must stay first —
        build it before any options are added)."""
        if self._placeholder is None:
            return
        row = self._make_option(None, self._placeholder, placeholder=True)
        self._popup.container.insert(0, row)

    def _index_of(self, value: str | None) -> int:
        for i, (opt_value, _row) in enumerate(self._rows):
            if opt_value == value:
                return i
        return -1

    def _sync_trigger(self) -> None:
        label = self._label_by_value.get(self._value or "")
        if label is None:
            label = self._placeholder or ""
        self._selected_span.container = [label]
        self._selected_span.styles = _PLACEHOLDER_TEXT if self._value is None else Styles()

    def _apply_option_styles(self, index: int) -> None:
        value, row = self._rows[index]
        if value is None:
            return  # the placeholder stays disabled
        if index == self._active_index:
            row.styles = _OPTION_ACTIVE
        elif index in self._hovered:
            row.styles = _OPTION_HOVER
        else:
            row.styles = _OPTION

    def _open_popup(self) -> None:
        if self._open or self._disabled or not self._rows:
            return
        self._open = True
        self._popup.styles = _PANEL_OPEN
        self._trigger.styles = self._trigger.styles.model_copy(update={"background_image": _CHEVRON_UP})
        self._trigger.args = {**self._trigger.args, "aria-expanded": "true"}
        self._wrapper.args = {**self._wrapper.args, "data-neony-outside": "true"}

    def _close(self) -> None:
        if not self._open:
            return
        self._open = False
        self._popup.styles = _PANEL
        self._trigger.styles = self._trigger.styles.model_copy(update={"background_image": _CHEVRON})
        self._trigger.args = {**self._trigger.args, "aria-expanded": "false"}
        self._wrapper.args = {k: v for k, v in self._wrapper.args.items() if k != "data-neony-outside"}

    def _move_active(self, delta: int) -> None:
        """Move the highlight by *delta*, clamped at the ends — no
        wrap-around (ArrowUp must always return to the first option)."""
        selectable = [i for i, (opt_value, _row) in enumerate(self._rows) if opt_value is not None]
        if not selectable:
            return
        if self._active_index not in selectable:
            self._active_index = selectable[0] if delta > 0 else selectable[-1]
        else:
            pos = selectable.index(self._active_index)
            self._active_index = selectable[max(0, min(len(selectable) - 1, pos + delta))]
        for i in range(len(self._rows)):
            self._apply_option_styles(i)

    async def _select(self, value: str | None, event: DomEvent | None) -> None:
        if value is None:
            return
        self.value = value
        self._close()
        if event is not None:
            event.value = value
            await self._dispatch("change", event)

    # ---- events ----

    async def _on_event(self, event_type: str, event: DomEvent) -> None:
        if event_type == "click":
            if event.key == self._trigger.key:
                # Trigger toggle — option rows select through their own
                # _bind handlers (distinguished by key above).
                if self._open:
                    self._close()
                else:
                    self._open_popup()
            elif event.key in self._row_by_key:
                await self._select(self._row_by_key[event.key], event)
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
            self._focused = True
            self._trigger.styles = self._trigger.styles.model_copy(update={"box_shadow": Theme.focus_glow("accent")})
        elif event_type == "blur":
            self._focused = False
            self._trigger.styles = self._trigger.styles.model_copy(update={"box_shadow": None})
        await self._dispatch(event_type, event)

    def _index_of_row(self, key: str) -> int:
        for i, (_value, row) in enumerate(self._rows):
            if row.key == key:
                return i
        return -1

    async def _on_keydown(self, event: DomEvent) -> None:
        key = event.value
        if key in ("Enter", " "):
            if event.key in self._row_by_key:
                return  # focused option: the native button click selects
            if self._open:
                await self._select_active(event)
            else:
                self._open_popup()
        elif key == "ArrowDown":
            self._open_popup()
            self._move_active(1)
        elif key == "ArrowUp":
            self._open_popup()
            self._move_active(-1)
        elif key in ("PageDown", "PageUp"):
            self._open_popup()
            selectable = [i for i, (opt_value, _row) in enumerate(self._rows) if opt_value is not None]
            if selectable:
                self._active_index = selectable[-1] if key == "PageDown" else selectable[0]
                for i in range(len(self._rows)):
                    self._apply_option_styles(i)
        elif key in ("Escape", "Tab"):
            self._close()

    async def _select_active(self, event: DomEvent) -> None:
        if 0 <= self._active_index < len(self._rows):
            value, _row = self._rows[self._active_index]
            await self._select(value, event)
