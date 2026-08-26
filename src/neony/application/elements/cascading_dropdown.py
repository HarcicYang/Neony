"""CascadingDropdown — a selector with nested option branches."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Self

from neony.application.theme import stub
from neony.dom import Button as _ButtonElem
from neony.dom import Color, Div, DomEvent, Filter, Span, Styles
from neony.dom.css import Border, BoxShadow, Shadow

from .. import motion
from .base import ReactiveText, _mount_text
from .dropdown import _PANEL, _PANEL_OPEN, Dropdown
from .icon import Icon
from .menu import MenuBranch, MenuItem

# A selector popup must allow child panels to extend sideways.  In contrast,
# Menu's root is a cursor-positioned context menu with its own lifecycle.
_CASCADE_PANEL = _PANEL.model_copy(update={"overflow": "visible"})
_CASCADE_PANEL_OPEN = _CASCADE_PANEL.model_copy(update={"display": "flex", "animation": _PANEL_OPEN.animation})
_BRANCH_PANEL = Styles(
    position="absolute",
    top="0",
    left="calc(100% + 4px)",
    z_index=1101,
    display="none",
    flex_direction="column",
    padding="6px",
    gap="2px",
    min_width="160px",
    max_height="calc(100vh - 8px)",
    overflow="visible",
    border_radius="8px",
    border=Border(width="1px", color=stub.border_glass),
    background_color=stub.surface_glass_bg,
    backdrop_filter=Filter(blur="20px", saturate=1.2),
    box_shadow=BoxShadow(layers=[Shadow(x=0, y=8, blur=32, color=stub.shadow)]),
)
_BRANCH_PANEL_OPEN = _BRANCH_PANEL.model_copy(update={"display": "flex", "animation": motion.popup_animation()})
_ROW_WRAP = Styles(position="relative", display="flex", width="100%")
_OPTION = Styles(
    display="flex",
    align_items="center",
    justify_content="space-between",
    gap="8px",
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
_OPTION_HOVER = _OPTION.model_copy(update={"background_color": stub.surface_glass_bg})
_BRANCH_CHEVRON = Styles(
    margin_left="auto",
    color=stub.text_secondary,
    font_size="11px",
    line_height="1",
    transition=motion.transition("transform", duration=motion.stub.fast),
)
_BRANCH_CHEVRON_OPEN = _BRANCH_CHEVRON.model_copy(update={"transform": "rotate(90deg)"})


class CascadingDropdown(Dropdown):
    """Dropdown-backed selector with recursively nested :class:`MenuBranch` rows.

    It intentionally owns one popup lifecycle—the same trigger, backdrop and
    close path as :class:`Dropdown`. ``Menu`` remains a separate right-click
    context-menu component and is never mounted inside this selector.
    """

    def __init__(
        self,
        label: ReactiveText = "",
        *,
        items: Sequence[MenuItem] = (),
        width: str = "220px",
        glass: bool = False,
    ) -> None:
        super().__init__(label, items=(), width=width, glass=glass)
        # Dropdown wires mousedown directly on trigger/backdrop. On WebKitGTK
        # a press can instead arrive at a keyed trigger child, so receive both
        # through the stable wrapper bubble path. Menu rows are filtered below.
        self._trigger._handlers.pop("mousedown", None)
        self._click_away._handlers.pop("mousedown", None)
        self._bind(self._wrapper, "mousedown")
        self._trigger_keys = {self._trigger.key, self._label_span.key, self._chevron.key}
        self._trigger.args = {**self._trigger.args, "aria-haspopup": "menu"}
        self._popup.styles = _CASCADE_PANEL
        self._branches: dict[str, Div] = {}
        self._branch_parent: dict[str, str | None] = {}
        self._branch_chevrons: dict[str, Span] = {}
        self._branch_rows: set[str] = set()
        self._add_items(items, self._popup, parent_branch=None)

    def _add_items(self, items: Sequence[MenuItem], parent: Div, *, parent_branch: str | None) -> None:
        for item in items:
            if isinstance(item, MenuBranch):
                self._add_branch(item, parent, parent_branch)
            else:
                self._add_leaf(item, parent)

    def _add_leaf(self, item: MenuItem, parent: Div) -> None:
        if isinstance(item, tuple):
            value, label = item
        elif isinstance(item, str):
            value = label = item
        else:  # pragma: no cover - _add_items narrows this
            raise TypeError("CascadingDropdown leaf must be a string or (value, label) tuple")
        label_span = Span(container=[])
        _mount_text(label_span, label)
        row = _ButtonElem(type="button", container=[label_span], styles=_OPTION, args={"role": "menuitem"})
        row.bubble_events = True
        self._rows.append((value, row))
        self._row_by_key[row.key] = value
        self._label_by_value[value] = label
        for event_type in ("click", "mouseover", "mouseout"):
            row.on(event_type, self._make_row_handler(event_type, row.key))
        parent.container.append(row)

    def _add_branch(self, branch: MenuBranch, parent: Div, parent_branch: str | None) -> None:
        label_span = Span(container=[])
        _mount_text(label_span, branch.label)
        chevron = Span(container=[Icon._font("chevron_right").render("14px")], styles=_BRANCH_CHEVRON)
        row = _ButtonElem(
            type="button",
            container=[label_span, chevron],
            styles=_OPTION,
            args={"role": "menuitem", "aria-haspopup": "menu"},
        )
        row.bubble_events = True
        panel = Div(styles=_BRANCH_PANEL, container=[])
        row_key = row.key
        self._branches[row_key] = panel
        self._branch_parent[row_key] = parent_branch
        self._branch_chevrons[row_key] = chevron
        self._branch_rows.add(row_key)
        for event_type in ("click", "mouseover"):
            row.on(event_type, self._make_branch_handler(row_key))
        parent.container.append(Div(styles=_ROW_WRAP, container=[row, panel]))
        self._add_items(branch.items, panel, parent_branch=row_key)

    def _make_branch_handler(self, key: str):
        async def handler(event: DomEvent) -> None:
            event.key = key
            event.source = "user"
            self._open_branch(key)

        return handler

    def _open_branch(self, key: str) -> None:
        parent = self._branch_parent[key]
        for candidate in self._branches:
            if candidate != key and self._branch_parent[candidate] == parent:
                self._close_branch_tree(candidate)
        self._branches[key].styles = _BRANCH_PANEL_OPEN
        self._branch_chevrons[key].styles = _BRANCH_CHEVRON_OPEN

    def _close_branch_tree(self, key: str) -> None:
        self._branches[key].styles = _BRANCH_PANEL
        self._branch_chevrons[key].styles = _BRANCH_CHEVRON
        for child, parent in self._branch_parent.items():
            if parent == key:
                self._close_branch_tree(child)

    def _open_popup(self) -> None:
        if self._open:
            return
        self._open = True
        self._popup.styles = _CASCADE_PANEL_OPEN
        self._click_away.styles = self._click_away.styles.model_copy(update={"display": "block"})
        self._chevron.styles = self._chevron.styles.model_copy(update={"transform": "rotate(180deg)"})
        self._trigger.args = {**self._trigger.args, "aria-expanded": "true"}
        self._wrapper.args = {**self._wrapper.args, "data-neony-outside": "true"}

    def _close(self) -> None:
        if not self._open:
            return
        for key, parent in self._branch_parent.items():
            if parent is None:
                self._close_branch_tree(key)
        super()._close()
        self._popup.styles = _CASCADE_PANEL

    async def _on_event(self, event_type: str, event: DomEvent) -> None:
        if event_type == "mousedown":
            if event.key == self._click_away.key:
                self._close()
            elif event.key in self._trigger_keys:
                self._open_popup() if not self._open else self._close()
            return
        if event_type == "click":
            # Branch rows own their click. Dropdown's generic click fallback
            # treats every non-leaf key as a trigger toggle, which would make
            # opening a branch also close/reset the outer popup.
            if event.key in self._row_by_key:
                await self._select(self._row_by_key[event.key], event)
            return
        if event.key in self._branch_rows and event_type == "mouseover":
            return
        await super()._on_event(event_type, event)

    def on_change(self, fn: Any) -> Self:
        return super().on_change(fn)
