"""Tabs component — tab bar + panels with active-tab state."""

from __future__ import annotations

from neony.dom import Color, Div, DOMElement, DomEvent, Styles

from .base import Component

_TAB_BASE = Styles(
    padding="10px 24px",
    border_radius="8px 8px 0 0",
    font_size="14px",
    font_weight="500",
    cursor="pointer",
    background_color=Color(var="--color-surface"),
    color=Color(var="--color-text-secondary"),
)

_TAB_ACTIVE = _TAB_BASE.model_copy(
    update={
        "background_color": Color(var="--color-accent"),
        "color": Color(var="--color-text-primary"),
    }
)

_PANEL_BASE = Styles(
    display="none",
    flex_direction="column",
    align_items="stretch",
    gap="16px",
    padding="24px",
    background_color=Color(var="--color-surface"),
    border_radius="0 8px 8px 8px",
    width="100%",
)

_PANEL_ACTIVE = _PANEL_BASE.model_copy(update={"display": "flex"})


class Tabs(Component):
    """A set of named tabs; exactly one panel is visible at a time.

    Usage::

        tabs = Tabs()
        tabs.add("Counter", counter_panel)
        tabs.add("Inputs", inputs_panel)

    ``tabs.active`` (index) and ``tabs.active_key`` switch programmatically.
    """

    def __init__(self) -> None:
        super().__init__()
        self._titles: list[str] = []
        self._panels: list[DOMElement] = []
        self._tab_elems: list[Div] = []
        self._active: int = 0

        self._bar = Div(styles=Styles(display="flex", gap="4px"))
        self._root = Div(
            styles=Styles(display="flex", flex_direction="column", width="100%"),
            container=[self._bar],
        )

    # ---- public API ----

    def add(self, title: str, panel: Component | DOMElement) -> Tabs:
        """Append a tab and its panel (chainable)."""
        panel_el = panel.build() if isinstance(panel, Component) else panel

        tab = Div(container=[title], styles=_TAB_ACTIVE if not self._titles else _TAB_BASE)
        tab.on_click(self._make_tab_handler(len(self._titles)))
        self._tab_elems.append(tab)
        self._titles.append(title)
        self._panels.append(panel_el)

        self._bar.container.append(tab)
        self._root.container.append(panel_el)
        self._apply_visibility()
        return self

    @property
    def active(self) -> int:
        return self._active

    @active.setter
    def active(self, index: int) -> None:
        self._active = index
        self._apply_visibility()

    @property
    def active_key(self) -> str | None:
        return self._panels[self._active].key if self._panels else None

    # ---- internals ----

    def _make_tab_handler(self, index: int):
        async def handler(event: DomEvent) -> None:
            self.active = index
            await self._dispatch("change", event)

        return handler

    def _apply_visibility(self) -> None:
        for i, (tab, panel) in enumerate(zip(self._tab_elems, self._panels, strict=True)):
            tab.styles = _TAB_ACTIVE if i == self._active else _TAB_BASE
            panel.styles = _PANEL_ACTIVE if i == self._active else _PANEL_BASE
