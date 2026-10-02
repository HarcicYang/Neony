"""Breadcrumb — clickable navigation ancestry with a current-page tail."""

from __future__ import annotations

from collections.abc import Sequence

from neony.application.theme import stub
from neony.dom import Button as _ButtonElem
from neony.dom import Color, DomEvent, Nav, Span, Styles

from ._choices import ChoiceItem, ChoiceItemLike, choice_content, coerce_choice_item
from .base import Component

_ROOT = Styles(display="flex", align_items="center", gap="6px", flex_wrap="wrap")
_ITEM = Styles(
    display="inline-flex",
    align_items="center",
    gap="5px",
    padding="3px 5px",
    border="none",
    border_radius="5px",
    background_color=Color(name="transparent"),
    color=stub.text_secondary,
    font_size="13px",
    cursor="pointer",
)
_CURRENT = _ITEM.model_copy(update={"color": stub.text_primary, "font_weight": "600", "cursor": "default"})
_SEPARATOR = Styles(color=stub.text_secondary, font_size="12px", opacity=0.65)


class Breadcrumb(Component):
    """An ordered navigation trail; the final item is the current page."""

    _bound_events: frozenset[str] = frozenset({"change", "click"})

    def __init__(
        self,
        *items: ChoiceItemLike,
        separator: str = "/",
        disabled: bool = False,
    ) -> None:
        super().__init__()
        self._items: list[ChoiceItem] = []
        self._rows: list[_ButtonElem] = []
        self._separator = separator
        self._disabled = disabled
        self._root = Nav(styles=_ROOT, args={"aria-label": "Breadcrumb"}, container=[])
        self.items = items

    @property
    def items(self) -> list[ChoiceItem]:
        return list(self._items)

    @items.setter
    def items(self, items: Sequence[ChoiceItemLike]) -> None:
        self._items = [coerce_choice_item(item) for item in items]
        self._rows.clear()
        self._root.container = []
        last = len(self._items) - 1
        for index, item in enumerate(self._items):
            is_current = index == last
            content, _label = choice_content(item)
            if is_current:
                row = _ButtonElem(
                    type="button",
                    container=content,
                    styles=_CURRENT,
                    disabled=True,
                    args={"aria-current": "page"},
                )
            else:
                row = _ButtonElem(
                    type="button",
                    container=content,
                    styles=_ITEM,
                    disabled=self._disabled or item.disabled,
                    args={},
                )
                row.bubble_events = True
                row.on("click", self._make_click_handler(item))
                self._rows.append(row)
            if index:
                self._root.container.append(Span(container=[self._separator], styles=_SEPARATOR))
            self._root.container.append(row)

    def _make_click_handler(self, item: ChoiceItem):
        async def handler(event: DomEvent) -> None:
            event.source = "user"
            if item.disabled:
                return
            event.value = item.value
            await self._dispatch("change", event)

        return handler

    async def _on_event(self, event_type: str, event: DomEvent) -> None:
        await self._dispatch(event_type, event)
