"""Tabs component — tab bar + panels with active-tab state."""

from __future__ import annotations

from neony.dom import Animation, Color, Div, DOMElement, DomEvent, Styles, Transition

from .base import Component

_TAB_BASE = Styles(
    padding="10px 24px",
    border_radius="8px",
    font_size="14px",
    font_weight="500",
    cursor="pointer",
    background_color=Color(var="--color-surface"),
    color=Color(var="--color-text-secondary"),
    # Smooth the active/inactive background switch.
    transition=Transition(duration="0.15s", timing="ease"),
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
    border_radius="8px",
    width="100%",
)

# Entering panels fade + slide up from the built-in "neony-rise-in"
# keyframe (injected by the app with every window).  The switch from
# _PANEL_BASE (no animation) to _PANEL_ACTIVE changes the animation value,
# so the browser replays it on every activation.
_PANEL_ACTIVE = _PANEL_BASE.model_copy(
    update={
        "display": "flex",
        "animation": Animation(name="neony-rise-in", duration="0.25s", timing="ease-out"),
    }
)

_GLASS_PANEL_BASE = _PANEL_BASE.model_copy(
    update={
        "background_color": Color(var="--color-surface-glass-bg"),
        "backdrop_filter": "blur(16px)",
        "border": "1px solid var(--color-border-glass)",
    }
)

_GLASS_PANEL_ACTIVE = _GLASS_PANEL_BASE.model_copy(
    update={
        "display": "flex",
        "animation": Animation(name="neony-rise-in", duration="0.25s", timing="ease-out"),
    }
)


class Tabs(Component):
    #: Event types wired internally (via _bind / custom handlers) —
    #: Component.on() must not wire these again.
    _bound_events: frozenset[str] = frozenset({"click"})

    """A set of named tabs; exactly one panel is visible at a time.

    Usage::

        tabs = Tabs(("Counter", counter_panel), ("Inputs", inputs_panel))
        # or chain: tabs.add("Counter", counter_panel)

    ``tabs.selected_panel`` (the panel element) and ``tabs.selected_title``
    switch programmatically.  ``active`` / ``active_key`` are deprecated
    aliases — ``active_key`` returns the tab title (it used to return an
    opaque element id).  ``glass=True`` gives the panels a frosted,
    translucent surface.
    """

    def __init__(self, *panes: tuple[str, Component | DOMElement], glass: bool = False) -> None:
        self._glass = glass
        super().__init__()
        self._titles: list[str] = []
        self._panels: list[DOMElement] = []
        self._tab_elems: list[Div] = []
        self._active: int = 0

        # flex_wrap: many tabs wrap to a second row instead of overflowing
        self._bar = Div(styles=Styles(display="flex", gap="4px", flex_wrap="wrap"))
        self._root = Div(
            styles=Styles(display="flex", flex_direction="column", width="100%"),
            container=[self._bar],
        )

        for title, panel in panes:
            self.add(title, panel)

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
    def selected_panel(self) -> DOMElement | None:
        """The visible panel's element (``None`` with no tabs)."""
        return self._panels[self._active] if self._panels else None

    @selected_panel.setter
    def selected_panel(self, panel: DOMElement | Component) -> None:
        """Select by the registered panel — the Component or its root
        element.  Components are matched by identity (they are already
        built into the tabs; building again would raise)."""
        if isinstance(panel, Component):
            panel = panel._root
        try:
            self._active = self._panels.index(panel)
        except ValueError as exc:
            raise ValueError("Tabs.selected_panel: panel is not registered in this Tabs") from exc
        self._apply_visibility()

    @property
    def selected_title(self) -> str | None:
        """The visible tab's title (``None`` with no tabs)."""
        return self._titles[self._active] if self._titles else None

    @selected_title.setter
    def selected_title(self, title: str) -> None:
        try:
            self._active = self._titles.index(title)
        except ValueError as exc:
            raise ValueError(f"Tabs.selected_title: unknown title {title!r}") from exc
        self._apply_visibility()

    @property
    def selected_key(self) -> str | None:
        """The selected tab's key — the tab TITLE (titles serve as the
        keys here; ``bind_selected`` uses this).  Duplicate titles make
        the selection ambiguous — the first match wins on set; use
        distinct titles."""
        return self.selected_title

    @selected_key.setter
    def selected_key(self, value: str | None) -> None:
        if value is None:
            raise ValueError("Tabs.selected_key: there is always exactly one active tab — None cannot select anything")
        self.selected_title = value

    @property
    def active(self) -> int:
        """Deprecated alias of the selected index."""
        return self._active

    @active.setter
    def active(self, index: int) -> None:
        if not 0 <= index < len(self._panels):
            raise IndexError(f"Tabs.active: index {index} out of range")
        self._active = index
        self._apply_visibility()

    @property
    def active_key(self) -> str | None:
        """Deprecated alias of :attr:`selected_title` (now the title
        string, not an opaque element id)."""
        return self.selected_title

    # ---- internals ----

    def _make_tab_handler(self, index: int):
        async def handler(event: DomEvent) -> None:
            self._active = index
            self._apply_visibility()
            event.value = self._titles[index]
            # Tab buttons are wired with raw DOM on_click (not the
            # Component dispatcher) — mark the event as user-driven.
            event.source = "user"
            await self._dispatch("change", event)

        return handler

    def _apply_visibility(self) -> None:
        panel_active = _GLASS_PANEL_ACTIVE if self._glass else _PANEL_ACTIVE
        panel_base = _GLASS_PANEL_BASE if self._glass else _PANEL_BASE
        for i, (tab, panel) in enumerate(zip(self._tab_elems, self._panels, strict=True)):
            tab.styles = _TAB_ACTIVE if i == self._active else _TAB_BASE
            panel.styles = panel_active if i == self._active else panel_base
