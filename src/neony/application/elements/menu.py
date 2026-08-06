"""Menu component — a fixed, cursor-positioned popup of options.

The root IS the panel (``position: fixed``), positioned with
:meth:`Menu.open_at` from viewport coordinates — typically the
``x`` / ``y`` of a ``contextmenu`` DomEvent, so no measurement channel
is needed.  Rows are native ``<button>`` elements with the same
keyboard navigation as :class:`Dropdown`; closes on selection,
Escape, or click-away (``outsideclick``).

NOTE: opening near the screen's right/bottom edge may overflow the
viewport (no auto-flip in v1).
"""

from __future__ import annotations

from neony.dom import Animation, Color, Div, DomEvent, Styles, Transition
from neony.dom import Button as _ButtonElem

from .base import Component

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
    border="1px solid var(--color-border-glass)",
    background_color=Color(var="--color-surface-glass-bg"),
    backdrop_filter="blur(20px) saturate(1.2)",
    box_shadow="0 8px 32px var(--color-shadow)",
)
_PANEL_OPEN = _PANEL.model_copy(
    update={
        "display": "flex",
        "animation": Animation(name="neony-rise-in", duration="0.15s", timing="ease-out"),
    }
)

_OPTION = Styles(
    display="flex",
    align_items="center",
    padding="8px 12px",
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


class Menu(Component):
    #: Wired internally.  ``change`` is dispatched manually.
    _bound_events: frozenset[str] = frozenset({"change", "click", "keydown", "outsideclick", "mouseover", "mouseout"})

    """A cursor-positioned popup menu.

    - ``menu.open_at(x, y)`` shows it at viewport coordinates (from a
      ``contextmenu`` event's ``x`` / ``y``)
    - ``menu.close()`` hides it
    - ``on_change(fn)`` fires on selections with the option's value
    """

    def __init__(self, *items: str | tuple[str, str]) -> None:
        super().__init__()
        self._rows: list[tuple[str, _ButtonElem]] = []
        self._row_by_key: dict[str, str] = {}
        self._hovered: set[int] = set()
        self._active_index = -1
        self._open = False

        self._root = Div(styles=_PANEL, container=[])
        # Keydowns from a focused option bubble up here.
        self._root.bubble_events = True

        self._bind(self._root, "keydown")
        self._bind(self._root, "outsideclick")
        for entry in items:
            self._add_option(entry)

    # ---- public API ----

    def open_at(self, x: float, y: float) -> None:
        """Show the menu above the cursor at viewport coordinates
        (e.g. a contextmenu event's ``x`` / ``y``).

        The panel anchors its BOTTOM edge 8px above the cursor and
        clamps its max-width/height to the space right/above it
        (``calc(100% - x)`` — 100% of a fixed element is the viewport),
        so it pops upward and never overflows the screen; no
        measurement channel needed.
        """
        if self._active_index < 0 and self._rows:
            # Pre-highlight the first option on open.
            self._active_index = 0
            self._apply_option_styles(0)
        self._root.styles = _PANEL_OPEN.model_copy(
            update={
                "left": f"{x:.0f}px",
                "top": None,  # pop upward: anchor the bottom edge instead
                "bottom": f"calc(100% - {y:.0f}px - 8px)",
                "max_width": f"calc(100% - {x:.0f}px - 8px)",
                "max_height": f"calc({max(0.0, y - 8):.0f}px)",
            }
        )
        self._root.args = {**self._root.args, "data-neony-outside": "true"}
        self._open = True

    def close(self) -> None:
        """Hide the menu."""
        if not self._open:
            return
        self._open = False
        self._root.styles = _PANEL
        self._root.args = {k: v for k, v in self._root.args.items() if k != "data-neony-outside"}

    # ---- internals ----

    def _add_option(self, entry: str | tuple[str, str]) -> None:
        if isinstance(entry, tuple):
            value, label = entry
        else:
            value = label = entry
        row = _ButtonElem(type="button", container=[label], styles=_OPTION, args={"role": "menuitem"})
        self._rows.append((value, row))
        self._row_by_key[row.key] = value
        self._bind(row, "click")
        self._bind(row, "mouseover")
        self._bind(row, "mouseout")
        self._root.container.append(row)

    def _apply_option_styles(self, index: int) -> None:
        _value, row = self._rows[index]
        if index == self._active_index:
            row.styles = _OPTION_ACTIVE
        elif index in self._hovered:
            row.styles = _OPTION_HOVER
        else:
            row.styles = _OPTION

    def _move_active(self, delta: int) -> None:
        """Move the highlight by *delta*, clamped at the ends — no
        wrap-around."""
        if not self._rows:
            return
        self._active_index = max(0, min(len(self._rows) - 1, self._active_index + delta))
        for i in range(len(self._rows)):
            self._apply_option_styles(i)

    async def _select(self, value: str, event: DomEvent | None) -> None:
        self.close()
        if event is not None:
            event.value = value
            await self._dispatch("change", event)

    # ---- events ----

    async def _on_event(self, event_type: str, event: DomEvent) -> None:
        if event_type == "click":
            if event.key in self._row_by_key:
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
            if event.key in self._row_by_key:
                return  # focused option: the native button click selects
            await self._select_active(event)
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
            self.close()

    async def _select_active(self, event: DomEvent) -> None:
        if 0 <= self._active_index < len(self._rows):
            value, _row = self._rows[self._active_index]
            await self._select(value, event)
