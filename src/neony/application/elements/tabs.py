"""Tabs component — tab bar + panels with active-tab state."""

from __future__ import annotations

from neony.application.theme import stub
from neony.dom import Div, DOMElement, DomEvent, Filter, Span, Styles, Transition

from ._panels import _PanelHost
from .base import Component
from .icon import Icon

_TAB_BASE = Styles(
    padding="10px 24px",
    border_radius="8px",
    font_size="14px",
    font_weight="500",
    cursor="pointer",
    background_color=stub.surface,
    color=stub.text_secondary,
    # Long titles (e.g. "Section J") stay on one line instead of wrapping
    # and collapsing the tab to two stacked rows.
    white_space="nowrap",
    # Smooth the active/inactive background switch.
    transition=Transition(duration="0.15s", timing="ease"),
)

_TAB_ACTIVE = _TAB_BASE.model_copy(
    update={
        "background_color": stub.accent,
        "color": stub.text_primary,
    }
)

# Panel visual styling — the _PanelHost slot owns visibility + the
# replaying rise-in animation; the panel element keeps its own chrome
# (padding / surface / glass tint).  Always flex so the slot's display
# toggle controls visibility.
_PANEL_BASE = Styles(
    display="flex",
    flex_direction="column",
    gap="16px",
    padding="24px",
    background_color=stub.surface,
    border_radius="8px",
    width="100%",
)

_PANEL_GLASS = _PANEL_BASE.model_copy(
    update={
        "background_color": stub.surface_glass_bg,
        "backdrop_filter": Filter(blur="16px"),
        "border": "1px solid var(--color-border-glass)",
    }
)


class Tabs(Component):
    """A set of named tabs; exactly one panel is visible at a time.

    Usage::

        tabs = Tabs(("Counter", counter_panel), ("Inputs", inputs_panel))
        # or chain: tabs.add("Counter", counter_panel)
        # or with explicit keys: Tabs(("Counter", counter_panel, "c"))

    ``tabs.selected_panel`` (the panel element), ``tabs.selected_title``
    and ``tabs.selected_key`` switch programmatically.  A tab's key is its
    explicit ``key`` if given, else its title — duplicate titles without
    explicit keys raise.  ``active`` / ``active_key`` are deprecated
    aliases — ``active_key`` returns the tab title (it used to return an
    opaque element id).  ``glass=True`` gives the panels a frosted,
    translucent surface.
    """

    def __init__(
        self,
        *panes: (tuple[str, Component | DOMElement] | tuple[str, Component | DOMElement, str]),
        glass: bool = False,
        fallback_panel: Component | DOMElement | None = None,
        edge_fade: bool = True,
    ) -> None:
        self._glass = glass
        super().__init__()
        self._titles: list[str] = []
        self._keys: list[str] = []
        self._panels: list[DOMElement] = []
        self._tab_elems: list[Div] = []
        self._active: int = 0
        self._host = _PanelHost()
        self._fallback_slot: Div | None = None

        bar_styles = Styles(
            display="flex",
            gap="4px",
            flex_wrap="nowrap",
            overflow_x="auto",
            overflow_y="hidden",
            min_width="0",
            # Horizontal padding reserves a breathing rim.  The edge fade
            # is now owned and applied dynamically by the JS scroll
            # indicator (data-neony-scroll), so this no longer has to
            # match a static mask width — it just keeps the first/last
            # tabs from kissing the strip edge.
            padding="0 36px",
        )
        # Horizontal tab strip: no-wrap + scroll so too many tabs scroll
        # sideways instead of wrapping into extra rows.  data-neony-wheel-x
        # routes a plain vertical wheel through the JS engine's smooth
        # horizontal scroll (WebKitGTK does not turn vertical wheel into
        # horizontal on its own) — no Shift required.  The scroll
        # indicator is explicit ("x-silent"): on a compact strip a resting
        # gutter is intrusive, so the thumb stays hidden until
        # hover/scroll and only the edge fade hints at rest.
        bar_args = {"data-neony-wheel-x": "true"}
        if edge_fade:
            bar_args["data-neony-scroll"] = "x-silent"
        self._bar = Div(styles=bar_styles, args=bar_args, scroll_indicator=edge_fade)
        self._root = Div(
            styles=Styles(display="flex", flex_direction="column", width="100%"),
            container=[self._bar, self._host.root],
        )

        if fallback_panel is not None:
            # Shown when selection is None (see selected_key setter).
            fallback_el = fallback_panel.build() if isinstance(fallback_panel, Component) else fallback_panel
            self._fallback_slot = self._host.add(fallback_el)

        for title, panel, *rest in panes:
            key = rest[0] if rest else None
            self.add(title, panel, key=key)

    # ---- public API ----

    def add(
        self,
        title: str,
        panel: Component | DOMElement,
        *,
        key: str | None = None,
        icon: Icon | None = None,
    ) -> Tabs:
        """Append a tab and its panel (chainable).

        *key* — optional explicit selection key (defaults to *title*);
        explicit keys let duplicate titles coexist.  Duplicate titles
        without explicit keys raise.
        *icon* renders before the title (an :class:`Icon` — image or glyph).
        """
        if key is None and title in self._titles:
            raise ValueError(f"Tabs.add: duplicate title {title!r} — pass an explicit key to disambiguate")
        panel_el = panel.build() if isinstance(panel, Component) else panel
        # Panel chrome (padding / glass tint) lives on the element; the
        # host slot owns visibility + the replayed rise-in animation.
        panel_el.styles = _PANEL_GLASS if self._glass else _PANEL_BASE

        if icon is not None:
            # Element-only children (reactive mode forbids mixing): the icon
            # Span + the title wrapped in a Span.
            content: list[DOMElement | str] = [icon.render("14px"), Span(container=[title])]
        else:
            content = [title]
        tab = Div(
            container=content,
            styles=_TAB_ACTIVE if not self._titles else _TAB_BASE,
            args={"tabindex": "0", "role": "tab"},
        )
        tab.on_click(self._make_tab_handler(len(self._titles)))
        tab.on("keydown", self._make_tab_keydown_handler(len(self._titles)))
        self._tab_elems.append(tab)
        self._titles.append(title)
        self._keys.append(key or title)
        self._panels.append(panel_el)

        self._bar.container.append(tab)
        self._host.add(panel_el)
        self._apply_visibility()
        return self

    @property
    def selected_panel(self) -> DOMElement | None:
        """The visible panel's element (``None`` with no tabs or with a
        fallback selected)."""
        if self._active < 0 or not self._panels:
            return None
        return self._panels[self._active]

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
        """The visible tab's title (``None`` with no tabs or with a
        fallback selected)."""
        if self._active < 0 or not self._titles:
            return None
        return self._titles[self._active]

    @selected_title.setter
    def selected_title(self, title: str) -> None:
        try:
            self._active = self._titles.index(title)
        except ValueError as exc:
            raise ValueError(f"Tabs.selected_title: unknown title {title!r}") from exc
        self._apply_visibility()

    @property
    def selected_key(self) -> str | None:
        """The selected tab's key — its explicit ``key`` if given, else
        its title (``bind_selected`` uses this).  ``None`` with no tabs or
        with a fallback_panel selected."""
        if self._active < 0 or not self._keys:
            return None
        return self._keys[self._active]

    @selected_key.setter
    def selected_key(self, value: str | None) -> None:
        if value is None:
            if self._fallback_slot is None:
                raise ValueError("Tabs.selected_key: None needs a fallback_panel to select nothing")
            self._active = -1
            self._apply_visibility()
            self._mirror_selected(value)
            return
        try:
            self._active = self._keys.index(value)
        except ValueError as exc:
            raise ValueError(f"Tabs.selected_key: unknown key {value!r}") from exc
        self._apply_visibility()
        self._mirror_selected(value)

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
            event.value = self._keys[index]
            # Tab buttons are wired with raw DOM on_click (not the
            # Component dispatcher) — mark the event as user-driven.
            event.source = "user"
            await self._dispatch("change", event)

        return handler

    def _make_tab_keydown_handler(self, index: int):
        async def handler(event: DomEvent) -> None:
            key = event.value  # the pressed key rides on event.value
            if key in ("Enter", " "):
                # Activate like a click (role="tab").
                self._active = index
                self._apply_visibility()
                event.value = self._keys[index]
                event.source = "user"
                await self._dispatch("change", event)
            elif key in ("ArrowRight", "ArrowLeft"):
                step = 1 if key == "ArrowRight" else -1
                nxt = (index + step) % len(self._tab_elems) if self._tab_elems else index
                self._active = nxt
                self._apply_visibility()
                self._tab_elems[nxt].args = {**self._tab_elems[nxt].args, "tabindex": "0"}
                # Move focus to the next tab.
                event.value = self._keys[nxt]
                event.source = "user"
                await self._dispatch("change", event)

        return handler

    def _apply_visibility(self) -> None:
        for i, tab in enumerate(self._tab_elems):
            tab.styles = _TAB_ACTIVE if i == self._active else _TAB_BASE
        if self._active < 0:
            # None selected — show the fallback slot (0) or hide all.
            self._host.set_active(0 if self._fallback_slot is not None else -1)
            return
        # Tab slots start after the fallback slot (index 0) when present.
        self._host.set_active(self._active + (1 if self._fallback_slot is not None else 0))
