"""CascadingDropdown — a fixed-trigger selector with nested menu branches."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Self

from neony.application.theme import Theme
from neony.dom import Div, DomEvent, Span

from .base import Component, ReactiveText, _mount_text
from .dropdown import (
    _CHEVRON_OPEN_STYLE,
    _CHEVRON_STYLE,
    _GLASS_TRIGGER,
    _PANEL,
    _PANEL_OPEN,
    _TRIGGER,
    _WRAP,
)
from .menu import Menu, MenuBranch, MenuItem

_CASCADE_PANEL = _PANEL.model_copy(
    update={
        "position": "absolute",
        "top": "calc(100% + 6px)",
        "left": "0",
        "z_index": 1100,
        # Branch panels extend outside this panel; scrolling here would clip them.
        "overflow": "visible",
    }
)
_CASCADE_PANEL_OPEN = _CASCADE_PANEL.model_copy(update={"display": "flex", "animation": _PANEL_OPEN.animation})


class CascadingDropdown(Component):
    """A dropdown trigger whose options may open nested child menus.

    ``MenuBranch`` supplies the hierarchy; leaf values are dispatched through
    ``on_change`` and shown on the trigger. The context-menu ``Menu`` remains
    independently positioned by ``open_at`` for right-click use cases.
    """

    _bound_events: frozenset[str] = frozenset({"click", "keydown", "outsideclick", "focus", "blur"})
    _value_event: str | None = "change"

    def __init__(
        self,
        label: ReactiveText = "",
        *,
        items: Sequence[MenuItem] = (),
        width: str = "220px",
        glass: bool = False,
    ) -> None:
        super().__init__()
        self._placeholder = label
        self._value: str | None = None
        self._label_by_value: dict[str, ReactiveText] = {}
        self._open = False
        self._focused = False
        self._label_span = Span(container=[])
        _mount_text(self._label_span, label)
        self._chevron = Span(container=["▾"], styles=_CHEVRON_STYLE)
        self._trigger = Div(
            styles=(_GLASS_TRIGGER if glass else _TRIGGER).model_copy(update={"width": width}),
            args={"tabindex": "0", "role": "combobox", "aria-haspopup": "menu", "aria-expanded": "false"},
            container=[self._label_span, self._chevron],
        )
        self._menu = Menu(*items)
        self._collect_labels(items)
        self._menu._root.styles = _CASCADE_PANEL
        self._wrapper = Div(styles=_WRAP, container=[self._trigger, self._menu._root])
        self._root = self._wrapper
        self._trigger.bubble_events = True
        self._wrapper.bubble_events = True
        self._menu.on_change(self._on_menu_change)
        self._bind(self._trigger, "click")
        self._bind(self._trigger, "keydown")
        self._bind(self._trigger, "focus")
        self._bind(self._trigger, "blur")
        self._bind(self._wrapper, "outsideclick")

    @property
    def value(self) -> str | None:
        return self._value

    @value.setter
    def value(self, value: str | None) -> None:
        self._value = value
        label = self._label_by_value.get(value or "")
        if label is not None:
            _mount_text(self._label_span, label)
        self._mirror_value(value)

    def _collect_labels(self, items: Sequence[MenuItem]) -> None:
        for item in items:
            if isinstance(item, MenuBranch):
                self._collect_labels(item.items)
            elif isinstance(item, tuple):
                self._label_by_value[item[0]] = item[1]
            elif isinstance(item, str):
                self._label_by_value[item] = item

    async def _on_menu_change(self, event: DomEvent) -> None:
        self.value = event.value
        self._close()
        await self._dispatch("change", event)

    def _open_popup(self) -> None:
        if self._open:
            return
        self._open = True
        self._menu._open = True
        self._menu._root.styles = _CASCADE_PANEL_OPEN
        self._menu._root.args = {**self._menu._root.args, "data-neony-outside": "true"}
        self._chevron.styles = _CHEVRON_OPEN_STYLE
        self._trigger.args = {**self._trigger.args, "aria-expanded": "true"}

    def _close(self) -> None:
        if not self._open:
            return
        self._open = False
        self._menu.close()
        self._menu._root.styles = _CASCADE_PANEL
        self._chevron.styles = _CHEVRON_STYLE
        self._trigger.args = {**self._trigger.args, "aria-expanded": "false"}
        self._wrapper.args = {k: v for k, v in self._wrapper.args.items() if k != "data-neony-outside"}

    async def _on_event(self, event_type: str, event: DomEvent) -> None:
        if event_type == "click":
            self._open_popup() if not self._open else self._close()
        elif event_type == "keydown":
            if event.value in ("Enter", " ", "ArrowDown", "ArrowUp"):
                self._open_popup()
            elif event.value in ("Escape", "Tab"):
                self._close()
        elif event_type == "outsideclick":
            self._close()
        elif event_type == "focus":
            self._focused = True
            self._trigger.styles = self._trigger.styles.model_copy(update={"box_shadow": Theme.focus_glow("accent")})
        elif event_type == "blur":
            self._focused = False
            self._trigger.styles = self._trigger.styles.model_copy(update={"box_shadow": None})
        await self._dispatch(event_type, event)

    def on_change(self, fn: Any) -> Self:
        return super().on_change(fn)
