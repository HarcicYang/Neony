"""Menu component — a fixed context menu with optional cascading branches."""

from __future__ import annotations

from collections.abc import Sequence

from neony.application.theme import stub
from neony.dom import (
    Animation,
    Border,
    BoxShadow,
    Color,
    Div,
    DomEvent,
    Filter,
    Shadow,
    Span,
    Styles,
    calc,
    px,
)
from neony.dom import Button as _ButtonElem

from .. import motion
from .base import Component, ReactiveText, _mount_text


class MenuBranch:
    """One context-menu row that opens a child menu beside itself."""

    def __init__(self, label: ReactiveText, items: Sequence[MenuItem]) -> None:
        self.label = label
        self.items = tuple(items)


MenuItem = ReactiveText | tuple[str, ReactiveText] | MenuBranch

_PANEL = Styles(
    position="fixed",
    z_index="600",
    display="none",
    flex_direction="column",
    padding="6px",
    gap="2px",
    min_width="160px",
    max_height="calc(100vh - 8px)",
    overflow="auto",
    border_radius="8px",
    border=Border(width="1px", color=stub.border_glass),
    background_color=stub.surface_glass_bg,
    backdrop_filter=Filter(blur="20px", saturate=1.2),
    box_shadow=BoxShadow(layers=[Shadow(x=0, y=8, blur=32, color=stub.shadow)]),
)
_PANEL_OPEN = _PANEL.model_copy(
    update={
        "display": "flex",
        "animation": Animation(name="neony-rise-in", duration=motion.stub.fast, timing=motion.stub.ease_enter),
    }
)
_SUBMENU = _PANEL.model_copy(
    update={
        "position": "absolute",
        "left": "calc(100% + 4px)",
        "top": "0",
        "z_index": 700,
        "overflow": "visible",
    }
)
_SUBMENU_OPEN = _SUBMENU.model_copy(
    update={
        "display": "flex",
        "animation": Animation(name="neony-rise-in", duration=motion.stub.fast, timing=motion.stub.ease_enter),
    }
)

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
_OPTION_ACTIVE = _OPTION.model_copy(update={"background_color": stub.accent_glass_bg})
_OPTION_HOVER = _OPTION.model_copy(update={"background_color": stub.surface_glass_bg})
_ROW_WRAP = Styles(position="relative", display="flex", width="100%")
_BRANCH_CHEVRON = Styles(
    margin_left="auto",
    color=stub.text_secondary,
    font_size="11px",
    line_height="1",
    transition=motion.transition("transform", duration=motion.stub.fast),
)
_BRANCH_CHEVRON_OPEN = _BRANCH_CHEVRON.model_copy(update={"transform": "rotate(90deg)"})


class Menu(Component):
    """A cursor-positioned context menu with optional cascading branches.

    Plain strings and ``(value, label)`` tuples remain leaf actions. Use
    :class:`MenuBranch` for a row that opens another menu beside itself.
    ``ArrowRight`` enters a branch, ``ArrowLeft`` returns to its parent, and
    Escape closes the current menu level before the whole menu tree.
    """

    _bound_events: frozenset[str] = frozenset({"change", "click", "keydown", "outsideclick", "mouseover", "mouseout"})

    def __init__(self, *items: MenuItem, _parent: Menu | None = None) -> None:
        super().__init__()
        self._parent = _parent
        self._rows: list[tuple[str, _ButtonElem]] = []
        self._row_by_key: dict[str, str] = {}
        self._branches: dict[str, Menu] = {}
        self._branch_chevrons: dict[str, Span] = {}
        self._hovered: set[int] = set()
        self._active_index = -1
        self._open = False
        self._submenu = _parent is not None

        self._root = Div(styles=_SUBMENU if self._submenu else _PANEL, container=[])
        self._root.bubble_events = True
        self._bind(self._root, "keydown")
        self._bind(self._root, "outsideclick")
        for entry in items:
            self._add_option(entry)

    def open_at(self, x: float, y: float) -> None:
        """Show the root context menu at viewport coordinates."""
        if self._submenu:
            self._open_submenu()
            return
        if self._active_index < 0 and self._rows:
            self._active_index = 0
            self._apply_option_styles(0)
        self._root.styles = _PANEL_OPEN.model_copy(
            update={
                "left": px(round(x)),
                "top": None,
                "bottom": calc(f"100% - {round(y)}px - 8px"),
                "max_width": calc(f"100% - {round(x)}px - 8px"),
                "max_height": calc(f"{max(0.0, y - 8):.0f}px"),
            }
        )
        self._root.args = {**self._root.args, "data-neony-outside": "true"}
        self._open = True

    def close(self) -> None:
        """Close this menu level and every descendant level."""
        for child in self._branches.values():
            child.close()
        if not self._open:
            return
        self._open = False
        if self._parent is not None:
            self._parent._set_branch_chevron(self, False)
        self._root.styles = _SUBMENU if self._submenu else _PANEL
        self._root.args = {k: v for k, v in self._root.args.items() if k != "data-neony-outside"}

    def _open_submenu(self) -> None:
        if self._parent is not None:
            self._parent._close_sibling_branches(self)
        self._root.styles = _SUBMENU_OPEN
        self._open = True
        if self._parent is not None:
            self._parent._set_branch_chevron(self, True)

    def _set_branch_chevron(self, branch: Menu, open: bool) -> None:
        for row_key, candidate in self._branches.items():
            if candidate is branch:
                self._branch_chevrons[row_key].styles = _BRANCH_CHEVRON_OPEN if open else _BRANCH_CHEVRON
                return

    def _close_sibling_branches(self, keep: Menu) -> None:
        """Keep one child branch open at each menu level."""
        for branch in self._branches.values():
            if branch is not keep:
                branch.close()

    def _add_option(self, entry: MenuItem) -> None:
        branch = entry if isinstance(entry, MenuBranch) else None
        if branch is not None:
            value, label = "", branch.label
        elif isinstance(entry, tuple):
            value, label = entry
        else:
            if not isinstance(entry, str):
                raise ValueError("Menu: a reactive item label needs a (value, label) tuple")
            value = label = entry

        label_span = Span(container=[])
        _mount_text(label_span, label)
        children = [label_span]
        branch_chevron: Span | None = None
        if branch is not None:
            branch_chevron = Span(container=["▶"], styles=_BRANCH_CHEVRON)
            children.append(branch_chevron)
        row = _ButtonElem(type="button", container=children, styles=_OPTION, args={"role": "menuitem"})
        row.bubble_events = True
        self._rows.append((value, row))
        self._row_by_key[row.key] = value
        for event_type in ("click", "mouseover", "mouseout"):
            row.on(event_type, self._make_row_handler(event_type, row.key))

        if branch is not None:
            assert branch_chevron is not None
            self._branch_chevrons[row.key] = branch_chevron
            self._branches[row.key] = Menu(*branch.items, _parent=self)
            wrapper = Div(
                styles=_ROW_WRAP,
                args={"data-neony-cascade-row": "true"},
                container=[row, self._branches[row.key]._root],
            )
            self._root.container.append(wrapper)
        else:
            self._root.container.append(row)

    def _make_row_handler(self, event_type: str, row_key: str):
        async def handler(event: DomEvent) -> None:
            event.key = row_key
            event.source = "user"
            await self._on_event(event_type, event)

        return handler

    def _apply_option_styles(self, index: int) -> None:
        _value, row = self._rows[index]
        if index == self._active_index:
            row.styles = _OPTION_ACTIVE
        elif index in self._hovered:
            row.styles = _OPTION_HOVER
        else:
            row.styles = _OPTION

    def _move_active(self, delta: int) -> None:
        if not self._rows:
            return
        self._active_index = max(0, min(len(self._rows) - 1, self._active_index + delta))
        for i in range(len(self._rows)):
            self._apply_option_styles(i)

    async def _select(self, value: str, event: DomEvent | None) -> None:
        root = self
        while root._parent is not None:
            root = root._parent
        root.close()
        if event is not None:
            event.value = value
            await root._dispatch("change", event)

    async def _on_event(self, event_type: str, event: DomEvent) -> None:
        if event_type == "click":
            if event.key in self._branches:
                self._branches[event.key]._open_submenu()
            elif event.key in self._row_by_key:
                await self._select(self._row_by_key[event.key], event)
        elif event_type == "mouseover":
            index = self._index_of_row(event.key)
            if index >= 0:
                self._hovered.add(index)
                self._apply_option_styles(index)
                if event.key in self._branches:
                    self._branches[event.key]._open_submenu()
        elif event_type == "mouseout":
            index = self._index_of_row(event.key)
            if index >= 0:
                self._hovered.discard(index)
                self._apply_option_styles(index)
        elif event_type == "keydown":
            await self._on_keydown(event)
        elif event_type == "outsideclick":
            self.close()
        await self._dispatch(event_type, event)

    def _index_of_row(self, key: str) -> int:
        for i, (_value, row) in enumerate(self._rows):
            if row.key == key:
                return i
        return -1

    async def _on_keydown(self, event: DomEvent) -> None:
        key = event.value
        if key in ("Enter", " "):
            if event.key in self._branches:
                self._branches[event.key]._open_submenu()
            elif event.key in self._row_by_key:
                await self._select_active(event)
        elif key == "ArrowRight":
            if 0 <= self._active_index < len(self._rows):
                row_key = self._rows[self._active_index][1].key
                if row_key in self._branches:
                    self._branches[row_key]._open_submenu()
        elif key == "ArrowLeft":
            if self._parent is not None:
                self.close()
        elif key == "ArrowDown":
            self._move_active(1)
        elif key == "ArrowUp":
            self._move_active(-1)
        elif key in ("PageDown", "PageUp"):
            if self._rows:
                self._active_index = len(self._rows) - 1 if key == "PageDown" else 0
                for i in range(len(self._rows)):
                    self._apply_option_styles(i)
        elif key in ("Escape", "Tab"):
            if self._parent is not None:
                self.close()
            else:
                self.close()

    async def _select_active(self, event: DomEvent) -> None:
        if 0 <= self._active_index < len(self._rows):
            row_key = self._rows[self._active_index][1].key
            if row_key not in self._branches:
                await self._select(self._row_by_key[row_key], event)
