"""Sidebar component — vertical navigation, glass-matched to TitleBar.

A Sidebar is a navigation rail that optionally owns its content panes:
register :class:`Pane` objects (or ``(label, panel)`` tuples) and the
sidebar swaps the visible pane internally, exactly like :class:`Tabs`.
With only :class:`SidebarItem` children it renders as a bare rail, as
before — content switching stays the user's job in that mode.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from typing import Any, Self

from pydantic import BaseModel, ConfigDict

from neony.dom import Color, Div, DOMElement, DomEvent, Span, Styles, Transition

from .. import shortcuts
from ._panels import _PanelHost
from .base import Component

_ITEM_BASE = Styles(
    display="flex",
    align_items="center",
    gap="10px",
    padding="10px 12px",
    border_radius="8px",
    font_size="14px",
    font_weight="500",
    cursor="pointer",
    background_color=Color(name="transparent"),
    color=Color(var="--color-text-secondary"),
    # Always-present left border avoids a layout shift on activation.
    border_left="3px solid transparent",
    # Smooth the active/inactive background + border-color switch.
    transition=Transition(duration="0.15s", timing="ease"),
)

_ITEM_ACTIVE = _ITEM_BASE.model_copy(
    update={
        # Frosted like the rest of the chrome, not a flat fill.
        "background_color": Color(var="--color-surface-glass-bg"),
        "backdrop_filter": "blur(20px) saturate(1.2)",
        "color": Color(var="--color-text-primary"),
        "border_left": "3px solid var(--color-accent)",
    }
)

_GLASS = Styles(
    display="flex",
    flex_direction="column",
    gap="4px",
    padding="10px 8px",
    background_color=Color(var="--color-surface-glass-bg"),
    backdrop_filter="blur(20px) saturate(1.2)",
    border_right="1px solid var(--color-border-glass)",
)

_SOLID = Styles(
    display="flex",
    flex_direction="column",
    gap="4px",
    padding="10px 8px",
    background_color=Color(var="--color-surface"),
    border_right="1px solid var(--color-border)",
)

# Transparent row wrapper: holds the rail and (in pane mode) the content
# host.  Shrink-wraps when bare, grows when panes are registered.
_WRAPPER = Styles(display="flex", flex_direction="row", align_items="stretch", min_height="0")

_GROUP_ROOT = Styles(display="flex", flex_direction="column", gap="4px")

_GROUP_LABEL = Styles(
    font_size="11px",
    font_weight="600",
    color=Color(var="--color-text-secondary"),
    text_transform="uppercase",
    letter_spacing="0.08em",
    padding="12px 12px 4px 12px",
)


class Pane(BaseModel):
    """One selectable Sidebar entry and its content panel.

    - ``label`` — the sidebar entry text (first positional argument)
    - ``panel`` — the component (or DOMElement) shown while this pane is
      active; built exactly once when the pane is registered
    - ``key`` — pane identity for ``selected_key`` / ``change`` payloads.
      Defaults to a random id so labels never collide; pass an explicit
      key when you want a readable identifier.
    - ``icon`` — optional glyph shown before the label
    - ``section`` — optional group title; consecutive panes sharing a
      section render under one small uppercase sidebar label
    - ``shortcut`` — optional window-level combo (same forms as
      ``Page.on_shortcut``), collected via :meth:`Sidebar.shortcuts`
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    label: str
    panel: Component | DOMElement | None = None
    key: str | None = None
    icon: str | None = None
    section: str | None = None
    shortcut: str | dict[str, str] | None = None

    def __init__(
        self,
        label: str = "",
        *,
        panel: Component | DOMElement | None = None,
        key: str | None = None,
        icon: str | None = None,
        section: str | None = None,
        shortcut: str | dict[str, str] | None = None,
    ) -> None:
        # Hand-written __init__ so ``label`` is positional, like the
        # component constructors (pydantic v2 only takes keywords).
        super().__init__(label=label, panel=panel, key=key, icon=icon, section=section, shortcut=shortcut)


class SidebarItem(Component):
    #: Event types wired internally (via _bind / custom handlers) —
    #: Component.on() must not wire these again.
    _bound_events: frozenset[str] = frozenset({"click", "mouseover", "mouseout"})

    """One clickable entry in a :class:`Sidebar`; ``key`` defaults to the
    lowercased label, ``icon`` is an optional glyph shown first."""

    def __init__(
        self,
        label: str,
        *,
        key: str | None = None,
        icon: str | None = None,
        active: bool = False,
    ) -> None:
        super().__init__()
        self._label = label
        self._key = key or label.lower()
        self._icon = icon
        self._active = active
        self._hover = False

        self._root = Div(
            styles=_ITEM_ACTIVE if active else _ITEM_BASE,
            container=self._text_content(),
        )
        # Clicks land on the icon/label spans — bubble them to this item.
        self._root.bubble_events = True
        self._bind(self._root, "click")
        self._bind(self._root, "mouseover")
        self._bind(self._root, "mouseout")

    # ---- internals ----

    def _text_content(self) -> list[DOMElement | str]:
        # Element-only children (reactive mode forbids mixing).
        parts: list[DOMElement | str] = []
        if self._icon:
            parts.append(
                Span(
                    container=[self._icon],
                    styles=Styles(font_size="16px", width="20px", text_align="center"),
                )
            )
        if self._label:
            parts.append(
                Span(
                    container=[self._label],
                    styles=Styles(font_size="14px"),
                )
            )
        return parts

    def _apply_styles(self) -> None:
        styles = _ITEM_ACTIVE if self._active else _ITEM_BASE
        if self._hover and not self._active:
            styles = styles.model_copy(update={"background_color": Color(var="--color-surface")})
        self._root.styles = styles

    # ---- state ----

    @property
    def key(self) -> str:
        return self._key

    @property
    def label(self) -> str:
        return self._label

    @label.setter
    def label(self, value: str) -> None:
        self._label = value
        self._root.container = self._text_content()

    @property
    def active(self) -> bool:
        return self._active

    @active.setter
    def active(self, value: bool) -> None:
        self._active = value
        self._apply_styles()

    # ---- events ----

    async def _on_event(self, event_type: str, event: DomEvent) -> None:
        if event_type == "mouseover":
            self._hover = True
            self._apply_styles()
        elif event_type == "mouseout":
            self._hover = False
            self._apply_styles()
        await self._dispatch(event_type, event)


class SidebarGroup(Component):
    """A titled section of a :class:`Sidebar` — a small uppercase label
    above its items.  ``add`` is chainable and works after the group is
    attached to a sidebar (new items are wired into it automatically)."""

    def __init__(self, label: str, *items: SidebarItem) -> None:
        super().__init__()
        self._label = label
        self._items: list[SidebarItem] = []
        # Set by Sidebar._attach — called with each item added from now
        # on, so the sidebar wires it without building it again.
        self._on_item_added: Callable[[SidebarItem], None] | None = None

        self._root = Div(styles=_GROUP_ROOT, container=[Span(container=[label], styles=_GROUP_LABEL)])
        for item in items:
            self.add(item)

    # ---- public API ----

    def add(self, item: SidebarItem) -> Self:
        """Append an item (chainable).  Items are built here — a sidebar
        adopting this group wires them, never builds them again."""
        el = item.build()
        self._items.append(item)
        self._root.container.append(el)
        if self._on_item_added is not None:
            self._on_item_added(item)
        return self

    # ---- internals ----

    def _attach(self, sidebar: Sidebar) -> None:
        """Adopt by *sidebar*: wire items added from now on into it."""
        self._on_item_added = sidebar._adopt_item

    # ---- state ----

    @property
    def label(self) -> str:
        return self._label

    @property
    def items(self) -> list[SidebarItem]:
        return list(self._items)


class Sidebar(Component):
    #: Event types wired internally (via _bind / custom handlers) —
    #: Component.on() must not wire these again.
    _bound_events: frozenset[str] = frozenset({"click", "mouseover", "mouseout"})

    """Vertical navigation rail; exactly one entry is selected at a time.
    Optionally owns content panes.

    Bare-rail usage (only :class:`SidebarItem` children) renders the rail
    alone — content switching stays the user's job::

        sidebar = Sidebar(
            SidebarItem("Home", icon="🏠"),
            SidebarItem("Settings", icon="⚙️"),
        )
        sidebar.on_change(lambda e: switch_content(e.value))  # key string

    Pane usage — the sidebar owns its content; clicking an entry (or
    pressing its shortcut) swaps the visible pane internally::

        sidebar = Sidebar(
            Pane("Home", panel=home_panel, icon="🏠", shortcut="Ctrl+1"),
            Pane("Settings", panel=settings_panel, icon="⚙️"),
        )
        sidebar.on_change(lambda e: print(e.value))  # pane key
        sidebar.selected_key = "settings"  # programmatic, no callback
    """

    def __init__(
        self,
        *children: SidebarItem | SidebarGroup | Pane | tuple[str, Component | DOMElement],
        width: str = "200px",
        active_key: str | None = None,
        glass: bool = True,
        corner_radius: str | None = None,
    ) -> None:
        super().__init__()
        self._width = width
        self._glass = glass
        self._corner_radius = corner_radius
        self._items: list[SidebarItem] = []
        self._panes: dict[str, Pane] = {}
        self._pane_keys: list[str] = []
        self._selected_key: str | None = None
        self._host: _PanelHost | None = None
        self._shortcuts: list[tuple[str | dict[str, str], Callable[[], Any]]] = []
        # Section-grouping state: the open group (None = flat) and the
        # section string that opened it.
        self._open_group: SidebarGroup | None = None
        self._open_section: str | None = None

        self._rail = Div(styles=(_GLASS if glass else _SOLID).model_copy(update={"width": width, "flex_shrink": "0"}))
        if corner_radius is not None:
            # Rounds the corner where the sidebar meets the titlebar.
            self._rail.styles = self._rail.styles.model_copy(update={"border_top_right_radius": corner_radius})

        self._root = Div(styles=_WRAPPER, container=[self._rail])

        for child in children:
            if isinstance(child, Pane):
                self.add_pane(child)
            elif isinstance(child, tuple):
                label, panel = child
                self.add_pane(Pane(label, panel=panel))
            else:
                self.add(child)
        if active_key is not None:
            self.selected_key = active_key

    # ---- public API ----

    def add(self, item: SidebarItem | SidebarGroup) -> Self:
        """Append an item or a titled group of items (chainable)."""
        if isinstance(item, SidebarGroup):
            item._attach(self)
            for sub in item.items:
                self._adopt_item(sub)
            self._rail.container.append(item.build())
            # A group is a flat-entry break: following panes don't join it.
            self._open_group = None
            self._open_section = None
            return self
        self._register_item(item)
        return self

    def add_pane(
        self,
        pane: Pane | str,
        panel: Component | DOMElement | None = None,
        *,
        key: str | None = None,
        icon: str | None = None,
        section: str | None = None,
        shortcut: str | dict[str, str] | None = None,
    ) -> Self:
        """Register a selectable pane with a content panel (chainable).

        *pane* is a :class:`Pane` model, or a label string with *panel*
        and the keyword options.  The panel is built exactly once and
        reused across switches; a panel component cannot be registered
        in two sidebars.
        """
        if isinstance(pane, str):
            pane = Pane(pane, panel=panel, key=key, icon=icon, section=section, shortcut=shortcut)
        resolved_key = pane.key or uuid.uuid4().hex
        if resolved_key in self._panes:
            raise ValueError(f"Sidebar: duplicate pane key {resolved_key!r}")
        if pane.shortcut is not None:
            # Fail fast on typos at registration.
            shortcuts.parse_combo(shortcuts.resolve_combo(pane.shortcut))

        host = self._ensure_host()
        # Persist the resolved key on the model so ``panes``/``selected``
        # report a stable identity.
        pane.key = resolved_key
        item = SidebarItem(pane.label, key=resolved_key, icon=pane.icon)
        self._register_item(item, section=pane.section)
        if pane.panel is None:
            # A pane without content still owns a (hidden) slot so the
            # selection model stays uniform.
            panel_el = Div()
        else:
            panel_el = pane.panel.build() if isinstance(pane.panel, Component) else pane.panel
        host.add(panel_el)
        self._panes[resolved_key] = pane
        self._pane_keys.append(resolved_key)
        if pane.shortcut is not None:
            self._shortcuts.append((pane.shortcut, self._make_shortcut_handler(resolved_key)))
        self._sync_panes()
        return self

    @property
    def items(self) -> list[SidebarItem]:
        return list(self._items)

    @property
    def panes(self) -> list[Pane]:
        return list(self._panes.values())

    @property
    def content(self) -> Div | None:
        """The pane host container (``None`` for a bare rail) — mount it
        wherever you like when using the sidebar outside the default
        rail+content layout."""
        return self._host.root if self._host is not None else None

    @property
    def selected(self) -> Pane | SidebarItem | None:
        """The selected entry — the :class:`Pane` when the selection owns
        a panel, the :class:`SidebarItem` otherwise."""
        for item in self._items:
            if item.key == self._selected_key:
                return self._panes.get(item.key, item)
        return None

    @selected.setter
    def selected(self, entry: Pane | SidebarItem) -> None:
        keys = {item.key for item in self._items}
        if entry.key not in keys:
            raise ValueError(f"Sidebar.selected: {entry!r} is not a registered entry")
        self.selected_key = entry.key

    @property
    def selected_key(self) -> str | None:
        return self._selected_key

    @selected_key.setter
    def selected_key(self, value: str | None) -> None:
        if value is not None and value not in {item.key for item in self._items}:
            raise ValueError(f"Sidebar.selected_key: unknown key {value!r}")
        self._selected_key = value
        for item in self._items:
            item.active = item.key == value
        self._sync_panes()

    @property
    def active_key(self) -> str | None:
        """Deprecated alias of :attr:`selected_key`."""
        return self._selected_key

    @active_key.setter
    def active_key(self, value: str | None) -> None:
        self.selected_key = value

    def shortcuts(self) -> list[tuple[str | dict[str, str], Callable[[], Any]]]:
        """``(combo, handler)`` pairs for panes that declared one — wire
        them with ``Page.on_shortcut`` (a future Shell does this for you).

        A shortcut switch behaves like a click: it selects the pane and
        fires ``change`` with ``source == "user"``.
        """
        return list(self._shortcuts)

    # ---- internals ----

    def _ensure_host(self) -> _PanelHost:
        if self._host is None:
            host = _PanelHost()
            self._host = host
            self._root.container.append(host.root)
            self._root.styles = self._root.styles.model_copy(update={"flex_grow": "1"})
        return self._host

    def _register_item(self, item: SidebarItem, *, section: str | None = None) -> None:
        """Wire *item* and place it — flat or into the open section
        group.  The item is built exactly once here (the group's own
        ``add`` builds it); adoption never builds it again."""
        if section is not None:
            if self._open_group is None or self._open_section != section:
                # A section switch starts a new group; consecutive panes
                # with the same section share one.
                self._open_group = SidebarGroup(section)
                self._open_group._attach(self)
                self._rail.container.append(self._open_group.build())
                self._open_section = section
            self._open_group.add(item)
        else:
            self._open_group = None
            self._open_section = None
            self._rail.container.append(item.build())
        self._adopt_item(item)

    def _adopt_item(self, item: SidebarItem) -> None:
        """Wire an already-built item: click handling, flat registry,
        first-item auto-selection."""
        item._root.on("click", self._make_item_handler(item))
        self._items.append(item)
        if self._selected_key is None:
            item.active = True
            self._selected_key = item.key
        else:
            item.active = item.key == self._selected_key

    def _sync_panes(self) -> None:
        """Mirror the selection onto the pane host: the slot for the
        selected key (if it owns a pane) is visible, the rest hidden."""
        if self._host is None:
            return
        if self._selected_key is None or self._selected_key not in self._panes:
            self._host.set_active(-1)
            return
        try:
            index = self._pane_keys.index(self._selected_key)
        except ValueError:
            # Selected bare item — no pane to show.
            self._host.set_active(-1)
            return
        self._host.set_active(index)

    def _make_item_handler(self, item: SidebarItem):
        async def handler(event: DomEvent) -> None:
            self.selected_key = item.key
            event.value = item.key
            # The item's own dispatcher may have run first and reset the
            # source back to "program" — a click is user input either way.
            event.source = "user"
            await self._dispatch("change", event)

        return handler

    def _make_shortcut_handler(self, key: str):
        async def handler() -> None:
            self.selected_key = key
            event = DomEvent(key=self._root.key, type="change", value=key)
            # A keypress is user input, not a programmatic change —
            # observers of on_change see it like a click.
            event.source = "user"
            await self._dispatch("change", event)

        return handler
