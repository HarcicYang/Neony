"""SegmentedControl — a single-select group of adjacent choices."""

from __future__ import annotations

import json
from collections.abc import Sequence

from neony.application.theme import stub
from neony.dom import Border, Color, Div, DomEvent, Filter, Styles
from neony.dom import Button as _ButtonElem

from .. import motion
from ._choices import ChoiceItem, ChoiceItemLike, choice_content, coerce_choice_item
from .base import Component

_ROOT = Styles(
    display="inline-flex",
    align_items="stretch",
    gap="3px",
    padding="3px",
    border_radius="9px",
    border=Border(width="1px", color=stub.border),
    background_color=stub.surface,
)
_GLASS_ROOT = _ROOT.model_copy(
    update={
        "background_color": stub.surface_glass_bg,
        "backdrop_filter": Filter(blur="8px"),
    }
)
_SEGMENT = Styles(
    display="flex",
    align_items="center",
    justify_content="center",
    gap="6px",
    min_height="30px",
    padding="6px 14px",
    border="none",
    border_radius="6px",
    background_color=Color(name="transparent"),
    color=stub.text_secondary,
    font_size="13px",
    font_weight="500",
    cursor="pointer",
    white_space="nowrap",
    transition=motion.transition(duration=motion.stub.fast),
)
_SEGMENT_ACTIVE = _SEGMENT.model_copy(update={"background_color": stub.accent, "color": stub.on_accent})
_SEGMENT_DISABLED = _SEGMENT.model_copy(update={"color": stub.text_secondary, "cursor": "default", "opacity": 0.5})


class SegmentedControl(Component):
    """A compact single-value control with button-like segments."""

    _bound_events: frozenset[str] = frozenset({"change", "click", "keydown"})
    _value_event: str | None = "change"

    def __init__(
        self,
        *items: ChoiceItemLike,
        value: str | None = None,
        glass: bool = False,
        disabled: bool = False,
    ) -> None:
        super().__init__()
        self._items: list[ChoiceItem] = []
        self._rows: list[_ButtonElem] = []
        self._value: str | None = None
        self._disabled = disabled
        self._root = Div(
            styles=_GLASS_ROOT if glass else _ROOT,
            args={"role": "radiogroup"},
            container=[],
        )
        self._root.bubble_events = True
        self._bind(self._root, "keydown")
        self.items = items
        if value is not None:
            self.value = value

    @property
    def items(self) -> list[ChoiceItem]:
        return list(self._items)

    @items.setter
    def items(self, items: Sequence[ChoiceItemLike]) -> None:
        self._items = [coerce_choice_item(item) for item in items]
        self._rows.clear()
        self._root.container = []
        for item in self._items:
            content, _label = choice_content(item)
            row = _ButtonElem(
                type="button",
                container=content,
                styles=self._row_style(item, active=item.value == self._value, disabled=self._disabled),
                disabled=item.disabled or self._disabled,
                args={
                    "role": "radio",
                    "aria-checked": "true" if item.value == self._value else "false",
                },
            )
            row.bubble_events = True
            row.on("click", self._make_click_handler(item))
            self._rows.append(row)
            self._root.container.append(row)

    @property
    def value(self) -> str | None:
        return self._value

    @value.setter
    def value(self, value: str | None) -> None:
        if value is not None and value not in {item.value for item in self._items}:
            raise ValueError(f"SegmentedControl: unknown value {value!r}")
        self._value = value
        for item, row in zip(self._items, self._rows, strict=True):
            row.styles = self._row_style(item, active=item.value == value, disabled=self._disabled)
            row.args = {**row.args, "aria-checked": "true" if item.value == value else "false"}
        self._mirror_value(value)

    @property
    def disabled(self) -> bool:
        return self._disabled

    @disabled.setter
    def disabled(self, value: bool) -> None:
        self._disabled = value
        for item, row in zip(self._items, self._rows, strict=True):
            row.disabled = value or item.disabled
            row.styles = self._row_style(item, active=item.value == self._value, disabled=value)

    @staticmethod
    def _row_style(item: ChoiceItem, *, active: bool, disabled: bool = False) -> Styles:
        if item.disabled or disabled:
            return _SEGMENT_DISABLED
        return _SEGMENT_ACTIVE if active else _SEGMENT

    def _make_click_handler(self, item: ChoiceItem):
        async def handler(event: DomEvent) -> None:
            event.source = "user"
            if item.disabled or self._disabled:
                return
            self.value = item.value
            event.value = item.value
            await self._dispatch("change", event)

        return handler

    async def _on_event(self, event_type: str, event: DomEvent) -> None:
        if event_type == "keydown":
            await self._on_keydown(event)
        await self._dispatch(event_type, event)

    async def _on_keydown(self, event: DomEvent) -> None:
        key = event.value
        if key not in ("ArrowLeft", "ArrowRight", "Home", "End"):
            return
        selectable = [(i, item) for i, item in enumerate(self._items) if not item.disabled]
        if not selectable:
            return
        current = next((pos for pos, (i, _item) in enumerate(selectable) if self._items[i].value == self._value), -1)
        if key == "Home":
            target = 0
        elif key == "End":
            target = len(selectable) - 1
        else:
            step = 1 if key == "ArrowRight" else -1
            target = (current + step) % len(selectable)
        item = selectable[target][1]
        self.value = item.value
        event.value = item.value
        row_key = self._rows[self._items.index(item)].key
        self._schedule_js(
            "(() => { const el = window.neony && window.neony.engine && "
            f"window.neony.engine.registry.get({json.dumps(row_key)}); "
            "if (el && typeof el.focus === 'function') el.focus(); })()"
        )
        await self._dispatch("change", event)
        event.value = key
