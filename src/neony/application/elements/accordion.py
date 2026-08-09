"""Accordion / Collapsible — expandable sections in a single scroll flow.

A :class:`Collapsible` is one titled row that toggles a content panel
between hidden and visible (replaying the built-in ``neony-drop-in``
entrance animation on every expand).  An :class:`Accordion` stacks
collapsibles; with ``multiple``
(the default) several can be open at once, with ``multiple=False`` only
one — opening a new one closes the others.

Only the ``display`` property switches (no height transitions), so this
is pure Python — no JS-layer involvement.
"""

from __future__ import annotations

from typing import Self

from neony.application.theme import stub
from neony.dom import Animation, Color, Div, DOMElement, DomEvent, Span, Styles, Transition

from .base import Component

# Accessibility / activation attributes for a collapsible header.  These
# live on the internal header element (behind the component), never on the
# public API — users construct ``Collapsible(title, *content, ...)`` and
# never see this dict.


def _header_attrs(expanded: bool) -> dict[str, str]:
    return {
        "tabindex": "0",
        "role": "button",
        "aria-expanded": "true" if expanded else "false",
    }


# ---- header (the clickable row) ----

_HEADER = Styles(
    display="flex",
    align_items="center",
    gap="8px",
    padding="12px 16px",
    border_radius="8px",
    cursor="pointer",
    font_size="14px",
    font_weight="600",
    background_color=Color(name="transparent"),
    color=stub.text_secondary,
    # Smooth the open/closed background + chevron rotation switch.
    transition=Transition(property="background-color", duration="0.15s", timing="ease"),
    user_select="none",
)

# Open header: a faint accent tint surfaces which groups are expanded.
_HEADER_OPEN = _HEADER.model_copy(
    update={
        "background_color": stub.surface,
        "color": stub.text_primary,
    }
)

# The chevron rotates 90° (▶→▼) on open — same transition as the header.
_CHEVRON = Styles(
    display="inline-flex",
    font_size="11px",
    color=stub.text_secondary,
    transition=Transition(property="transform", duration="0.15s", timing="ease"),
)
_CHEVRON_OPEN = _CHEVRON.model_copy(update={"transform": "rotate(90deg)"})

# ---- content panel ----

_CONTENT_HIDDEN = Styles(display="none", width="100%")

# Mirrors tabs.py _PANEL_ACTIVE / _panels.py _SLOT_ACTIVE: the switch from
# _CONTENT_HIDDEN (no animation) to _CONTENT_VISIBLE changes the animation
# value, so the browser replays neony-drop-in on every expand.
_CONTENT_VISIBLE = Styles(
    display="flex",
    flex_direction="column",
    width="100%",
    gap="12px",
    padding="8px 0 4px 0",
    animation=Animation(name="neony-drop-in", duration="0.25s", timing="ease-out"),
)

# ---- accordion root ----

_ACCORDION_ROOT = Styles(display="flex", flex_direction="column", gap="8px", width="100%")

_COLLAPSIBLE_ROOT = Styles(display="flex", flex_direction="column", width="100%")


class Collapsible(Component):
    """One expandable section: a clickable title row and a content panel.

    Usage::

        collapsible = Collapsible("Inputs", panel_a, panel_b)
        collapsible.on_change(lambda e: print(e.value))  # the key

    ``expanded`` toggles programmatically (DOM only, no callback); user
    clicks / keyboard toggle it and fire ``change`` with ``source ==
    "user"`` and ``event.value`` set to the key.  Read the new state via
    :attr:`expanded` or the parent accordion's :attr:`expanded_keys`.
    """

    _bound_events: frozenset[str] = frozenset({"click", "keydown"})

    def __init__(
        self,
        title: str,
        *content: Component | DOMElement | str,
        expanded: bool = False,
        key: str | None = None,
    ) -> None:
        super().__init__()
        self._title = title
        self._key = key or title.lower()
        self._expanded = expanded
        # The accordion this belongs to (set on adoption). None = standalone.
        self._accordion: Accordion | None = None

        self._chevron = Span(container=["▶"], styles=_CHEVRON_OPEN if expanded else _CHEVRON)
        self._title_span = Span(container=[title], styles=Styles(font_size="14px"))
        self._header = Div(
            container=[self._title_span, Span(container=[self._chevron], styles=Styles(margin_left="auto"))],
            styles=_HEADER_OPEN if expanded else _HEADER,
            args=_header_attrs(expanded),
        )
        # Children bubble their clicks to the header so a click on the
        # chevron / title text still toggles.
        self._header.bubble_events = True

        built = [c.build() if isinstance(c, Component) else c for c in content]
        self._content = Div(container=built, styles=_CONTENT_VISIBLE if expanded else _CONTENT_HIDDEN)

        self._root = Div(styles=_COLLAPSIBLE_ROOT, container=[self._header, self._content])
        self._bind(self._header, "click")
        self._bind(self._header, "keydown")

    # ---- public API ----

    @property
    def key(self) -> str:
        return self._key

    @property
    def title(self) -> str:
        return self._title

    @property
    def expanded(self) -> bool:
        return self._expanded

    @expanded.setter
    def expanded(self, value: bool) -> None:
        """Toggle programmatically — updates the DOM, never fires a
        callback (mirrors the project-wide rule for programmatic state)."""
        self._expanded = value
        self._apply_visibility()

    def toggle(self) -> None:
        """Flip the expanded state (programmatic — no callback)."""
        self.expanded = not self._expanded

    # ---- internals ----

    def _apply_visibility(self) -> None:
        self._header.styles = _HEADER_OPEN if self._expanded else _HEADER
        self._chevron.styles = _CHEVRON_OPEN if self._expanded else _CHEVRON
        self._content.styles = _CONTENT_VISIBLE if self._expanded else _CONTENT_HIDDEN
        self._header.args = _header_attrs(self._expanded)

    async def _on_event(self, event_type: str, event: DomEvent) -> None:
        if event_type == "click":
            activated = True
        elif event_type == "keydown":
            # The pressed key rides on event.value (event.key is the element
            # id) — Enter / Space activate a role="button".
            activated = event.value in ("Enter", " ")
        else:
            await self._dispatch(event_type, event)
            return

        if not activated:
            return

        self._expanded = not self._expanded
        self._apply_visibility()
        event.value = self._key
        event.source = "user"
        await self._dispatch("change", event)
        # Surface the toggle to the parent accordion (mutual exclusion + a
        # container-level ``change`` for listeners on the accordion).
        if self._accordion is not None:
            await self._accordion._on_child_change(self)


class Accordion(Component):
    """A stack of :class:`Collapsible` sections.

    Usage::

        Accordion(
            Collapsible("Inputs", inputs_panel, checks_panel),
            Collapsible("Layout", layout_panel, expanded=True),
        )

    Or fluently with :meth:`section` (the gallery-friendly form)::

        Accordion(multiple=True).section("Inputs", inputs_panel).section("Layout", layout_panel)

    ``multiple=True`` (default) lets several sections stay open; ``False``
    makes them mutually exclusive — opening one closes the others.

    Listen on the accordion for ``change`` (``event.value`` is the key of
    the section the user just toggled).  Read the full open set via
    :attr:`expanded_keys`.
    """

    _bound_events: frozenset[str] = frozenset()

    def __init__(self, *items: Collapsible, multiple: bool = True) -> None:
        super().__init__()
        self._multiple = multiple
        self._items: list[Collapsible] = []
        self._root = Div(styles=_ACCORDION_ROOT)
        for item in items:
            self.add(item)

    # ---- public API ----

    def add(self, item: Collapsible) -> Self:
        """Append a :class:`Collapsible` (chainable)."""
        self._adopt(item)
        self._root.container.append(item.build())
        return self

    def section(
        self,
        title: str,
        *content: Component | DOMElement | str,
        expanded: bool = False,
        key: str | None = None,
    ) -> Self:
        """Build a :class:`Collapsible` from ``title`` + ``content`` and
        append it (chainable) — the gallery-friendly shorthand that keeps
        one mental model (no ``(title, *content)`` tuples at the call site)."""
        return self.add(Collapsible(title, *content, expanded=expanded, key=key))

    @property
    def items(self) -> list[Collapsible]:
        return list(self._items)

    @property
    def multiple(self) -> bool:
        return self._multiple

    @property
    def expanded_keys(self) -> list[str]:
        """The keys of currently-open sections, in registration order."""
        return [item.key for item in self._items if item.expanded]

    @expanded_keys.setter
    def expanded_keys(self, keys: list[str]) -> None:
        """Set the open sections programmatically (no callback).  Keys not
        registered are ignored; ``multiple=False`` keeps only the last."""
        wanted: set[str] = set(keys)
        if not self._multiple and wanted:
            wanted = {keys[-1]}  # honour single-open mode.
        for item in self._items:
            item.expanded = item.key in wanted

    # ---- internals ----

    def _adopt(self, item: Collapsible) -> None:
        if item._accordion is not None:
            raise ValueError(f"Accordion: Collapsible {item.key!r} already belongs to another Accordion")
        item._accordion = self
        # Honour single-open at construction: if an earlier section is open,
        # this new one cannot also be.
        if not self._multiple and any(other.expanded for other in self._items):
            item._expanded = False
            item._apply_visibility()
        self._items.append(item)

    async def _on_child_change(self, child: Collapsible) -> None:
        """A child toggled on user input — enforce mutual exclusion, then
        re-dispatch ``change`` on the accordion with the child's key."""
        if not self._multiple and child.expanded:
            for other in self._items:
                if other is not child and other.expanded:
                    other.expanded = False
        event = DomEvent(key=self._root.key, type="change", value=child.key)
        event.source = "user"
        await self._dispatch("change", event)
