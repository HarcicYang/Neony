"""Dropdown component — a themed popup of options under a trigger.

The same pattern as Select's custom popup: a trigger Div (tabindex 0,
combobox role, chevron flip) with a glass panel of native ``<button>``
rows anchored below.  Keyboard: Enter/Space opens, ArrowDown/Up moves
the highlighted row (clamped at the ends — no wrap), PageUp/PageDown
jump to first/last, Enter picks, Escape/Tab closes, click-away closes
via the engine's synthetic ``outsideclick`` event.
"""

from __future__ import annotations

from collections.abc import Sequence

from neony.application.theme import Theme, stub
from neony.dom import Border, BoxShadow, Color, Div, DomEvent, Filter, Shadow, Span, Styles
from neony.dom import Button as _ButtonElem

from .. import motion
from .base import Component, ReactiveText, _mount_text
from .icon import Icon

_TRIGGER = Styles(
    display="flex",
    align_items="center",
    justify_content="space-between",
    gap="8px",
    padding="10px 14px",
    border_radius="8px",
    border=Border(width="1px", color=stub.border),
    background_color=stub.surface,
    color=stub.text_primary,
    font_size="15px",
    cursor="pointer",
    user_select="none",
    outline="none",
    transition=motion.transition("border-color", duration=motion.stub.fast),
)

_GLASS_TRIGGER = _TRIGGER.model_copy(
    update={
        "background_color": stub.surface_glass_bg,
        "backdrop_filter": Filter(blur="8px"),
        "border": f"1px solid {Theme.glass_border('neutral')}",
    }
)

_WRAP = Styles(position="relative", display="inline-block")
# A component-owned click-away layer replaces the unreliable document-level
# synthetic outsideclick route on WebKitGTK. It stays below the trigger/panel.
_CLICK_AWAY = Styles(position="fixed", top="0", right="0", bottom="0", left="0", z_index=1099, display="none")
_CLICK_AWAY_OPEN = _CLICK_AWAY.model_copy(update={"display": "block"})

_PANEL = Styles(
    position="absolute",
    top="calc(100% + 6px)",
    left="0",
    # Must sit above Dialog's panel content when mounted inside PromptDialog.
    z_index="1100",
    display="none",
    flex_direction="column",
    padding="6px",
    gap="2px",
    max_height="calc(100vh - 8px)",
    overflow="auto",
    border_radius="8px",
    border=Border(width="1px", color=stub.border_glass),
    background_color=stub.surface_glass_bg,
    backdrop_filter=Filter(blur="20px", saturate=1.2),
    box_shadow=BoxShadow(layers=[Shadow(x=0, y=8, blur=32, color=stub.shadow)]),
)
# Entrance animation replays on every open (display: none → flex swaps
# the animation value, Tabs precedent).
_PANEL_OPEN = _PANEL.model_copy(
    update={
        "display": "flex",
        "animation": motion.popup_animation(),
    }
)

_OPTION = Styles(
    display="flex",
    align_items="center",
    padding="8px 10px",
    border_radius="6px",
    border="none",
    background_color=Color(name="transparent"),
    color=stub.text_primary,
    font_size="14px",
    text_align="left",
    cursor="pointer",
    transition=motion.transition(duration=motion.stub.fast),
)
_OPTION_ACTIVE = _OPTION.model_copy(update={"background_color": stub.accent_glass_bg})
_OPTION_HOVER = _OPTION.model_copy(update={"background_color": stub.surface_glass_bg})

_CHEVRON_STYLE = Styles(
    color=stub.text_secondary,
    font_size="11px",
    line_height="1",
    transition=motion.transition("transform", duration=motion.stub.fast),
)
_CHEVRON_OPEN_STYLE = _CHEVRON_STYLE.model_copy(update={"transform": "rotate(180deg)"})


class Dropdown(Component):
    #: Wired internally.  ``change`` is dispatched manually.
    _bound_events: frozenset[str] = frozenset(
        {"change", "click", "keydown", "outsideclick", "mouseover", "mouseout", "focus", "blur"}
    )

    #: bind_value user channel — the manually dispatched selection
    #: (``_select`` sets ``event.value`` to the picked value).
    _value_event: str | None = "change"

    """A themed popup of options under a trigger.

    - ``dropdown.value`` reads / sets the selected option's value
      (immediate write, no callback)
    - ``on_change(fn)`` fires on user selections with the value string
    - options are ``str`` (value == label) or ``(value, label)`` tuples
    """

    def __init__(
        self,
        label: ReactiveText = "",
        *,
        items: Sequence[str | tuple[str, ReactiveText]] = (),
        width: str = "200px",
        glass: bool = False,
    ) -> None:
        super().__init__()
        self._label: ReactiveText = label
        self._options: list[tuple[str, ReactiveText]] = []
        self._label_by_value: dict[str, ReactiveText] = {}
        self._rows: list[tuple[str, _ButtonElem]] = []
        self._row_by_key: dict[str, str] = {}
        self._hovered: set[int] = set()
        self._active_index = -1
        self._value: str | None = None
        self._open = False
        self._focused = False

        self._label_span = Span(container=[])
        _mount_text(self._label_span, label)
        self._chevron = Span(container=[Icon._font("expand_more").render("14px")], styles=_CHEVRON_STYLE)
        self._trigger = Div(
            styles=(_GLASS_TRIGGER if glass else _TRIGGER).model_copy(
                update={"width": width, "position": "relative", "z_index": 1100}
            ),
            args={"tabindex": "0", "role": "combobox", "aria-haspopup": "listbox", "aria-expanded": "false"},
            container=[self._label_span, self._chevron],
        )
        self._popup = Div(styles=_PANEL, container=[])
        self._click_away = Div(styles=_CLICK_AWAY)
        self._wrapper = Div(styles=_WRAP, container=[self._click_away, self._trigger, self._popup])
        # Clicks on the label/chevron spans bubble to the trigger (which
        # owns the click handler); keydowns from a focused option bubble
        # up to the wrapper.
        self._trigger.bubble_events = True
        self._wrapper.bubble_events = True
        self._root = self._wrapper

        for entry in items:
            self._add_option(entry)

        # WebKitGTK/Wayland reliably delivers mousedown for popup controls,
        # whereas its synthesized click can arrive late or be skipped.
        # Rows remain click-driven; only open/close controls use mousedown.
        self._bind(self._trigger, "mousedown")
        self._bind(self._click_away, "mousedown")
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
        self._mirror_value(value)

    @property
    def items(self) -> list[tuple[str, ReactiveText]]:
        return list(self._options)

    @items.setter
    def items(self, items: Sequence[str | tuple[str, ReactiveText]]) -> None:
        self._popup.container.clear()
        self._rows.clear()
        self._row_by_key.clear()
        self._options.clear()
        self._label_by_value.clear()
        self._active_index = -1
        for entry in items:
            self._add_option(entry)

    # ---- internals ----

    def _add_option(self, entry: str | tuple[str, ReactiveText]) -> None:
        if isinstance(entry, tuple):
            value, label = entry
        else:
            value = label = entry
        self._options.append((value, label))
        self._label_by_value[value] = label
        # The label rides a child span so a reactive ``tr`` binding can
        # re-render on language switch.
        label_span = Span(container=[])
        _mount_text(label_span, label)
        row = _ButtonElem(type="button", container=[label_span], styles=_OPTION, args={"role": "option"})
        row.bubble_events = True  # label-span clicks/hovers reach the row
        self._rows.append((value, row))
        self._row_by_key[row.key] = value
        for event_type in ("click", "mouseover", "mouseout"):
            row.on(event_type, self._make_row_handler(event_type, row.key))
        self._popup.container.append(row)

    def _make_row_handler(self, event_type: str, row_key: str):
        """Per-row handler: the label rides a child span, so a click on
        the text arrives with the span's key — rewrite it to the row's
        own key so the shared ``_on_event`` row lookup works."""

        async def handler(event: DomEvent) -> None:
            event.key = row_key
            event.source = "user"
            await self._on_event(event_type, event)

        return handler

    def _index_of(self, value: str | None) -> int:
        for i, (opt_value, _row) in enumerate(self._rows):
            if opt_value == value:
                return i
        return -1

    def _sync_trigger(self) -> None:
        label = self._label_by_value.get(self._value or "")
        if label is not None:
            # Re-mount the selected label (possibly a reactive binding).
            _mount_text(self._label_span, label)

    def _apply_option_styles(self, index: int) -> None:
        _value, row = self._rows[index]
        if index == self._active_index:
            row.styles = _OPTION_ACTIVE
        elif index in self._hovered:
            row.styles = _OPTION_HOVER
        else:
            row.styles = _OPTION

    def _open_popup(self) -> None:
        if self._open or not self._rows:
            return
        self._open = True
        if self._active_index < 0:
            # Pre-highlight the first option on open.
            self._active_index = 0
            self._apply_option_styles(0)
        self._popup.styles = _PANEL_OPEN
        self._click_away.styles = _CLICK_AWAY_OPEN
        self._chevron.styles = _CHEVRON_OPEN_STYLE
        self._trigger.args = {**self._trigger.args, "aria-expanded": "true"}
        self._wrapper.args = {**self._wrapper.args, "data-neony-outside": "true"}

    def _close(self) -> None:
        if not self._open:
            return
        self._open = False
        self._popup.styles = _PANEL
        self._click_away.styles = _CLICK_AWAY
        self._chevron.styles = _CHEVRON_STYLE
        self._trigger.args = {**self._trigger.args, "aria-expanded": "false"}
        self._wrapper.args = {k: v for k, v in self._wrapper.args.items() if k != "data-neony-outside"}

    def _move_active(self, delta: int) -> None:
        """Move the highlight by *delta*, clamped at the ends — no
        wrap-around (ArrowUp must always return to the first option)."""
        if not self._rows:
            return
        self._active_index = max(0, min(len(self._rows) - 1, self._active_index + delta))
        for i in range(len(self._rows)):
            self._apply_option_styles(i)

    async def _select(self, value: str, event: DomEvent | None) -> None:
        self.value = value
        self._close()
        if event is not None:
            event.value = value
            await self._dispatch("change", event)

    # ---- events ----

    async def _on_event(self, event_type: str, event: DomEvent) -> None:
        if event_type == "mousedown":
            # Open/close controls use mousedown; option rows still use click
            # so selection preserves the normal button activation behavior.
            if event.key == self._click_away.key:
                self._close()
            else:
                if self._open:
                    self._close()
                else:
                    self._open_popup()
        elif event_type == "click":
            if event.key in self._row_by_key:
                await self._select(self._row_by_key[event.key], event)
            else:
                # The trigger's label/chevron spans bubble clicks with the
                # span's key (not the trigger's) — anything that isn't an
                # option row is a trigger toggle.
                if self._open:
                    self._close()
                else:
                    self._open_popup()
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
            if self._rows:
                self._active_index = len(self._rows) - 1 if key == "PageDown" else 0
                for i in range(len(self._rows)):
                    self._apply_option_styles(i)
        elif key in ("Escape", "Tab"):
            self._close()

    async def _select_active(self, event: DomEvent) -> None:
        if 0 <= self._active_index < len(self._rows):
            value, _row = self._rows[self._active_index]
            await self._select(value, event)
