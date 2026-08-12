"""Reorder component — a draggable flex board.

A :class:`Reorder` renders a flex container of draggable cards; dragging
a card onto another card's first half inserts it before that card, the
second half after it.  The engine picks the axis from the container's
``flex-direction`` (``offset_x`` for a row, ``offset_y`` for a column),
and a ``row`` board with ``wrap=True`` wraps into a grid — so a card can
be dragged both horizontally (within a row) and vertically (into another
row).  Constrain ``max_width`` to force the wrap.

Cards may be any content — plain or reactive text, a whole
:class:`~neony.application.elements.base.Component`, or a raw
:class:`~neony.dom.DOMElement` — not just :class:`ReorderItem`.  Bare
content needs no wrapper and no explicit key: strings use the label,
keyed DOM elements keep their own key, and everything else (a stack of
``Card``s, …) gets an auto-generated key.  Use the type parameter
(``Reorder[Card]``) to keep ``items`` typed.

Boards can exchange cards: dragging a card onto a card of another
:class:`Reorder` shows the landing slot in that board (the placeholder
travels across containers), and the drop moves the card between boards.
Cross-board moves need globally unique card keys.

The board owns the reorder end to end: cards are pre-marked draggable
with the payload declared up front, and ``drop`` reorders the container
internally.  Subscribe with :meth:`on_drop` to observe the new order
(``event.value`` is the ordered card keys).

Usage::

    board = Reorder("First", "Second", Card(title="Third"))  # bare content
    board.on_drop(lambda e: print(e.value))   # ordered keys after a drag
    board.order                               # current keys in render order
"""

from __future__ import annotations

from typing import ClassVar, Generic, Literal, Self, TypeVar

from neony.application.theme import stub
from neony.dom import Div, DOMElement, DomEvent, Styles
from neony.dom.reactive import Computed, Signal

from .base import Component, ReactiveText

#: What a card may contain: plain/reactive text, a built component, or a
#: raw DOM element.  Components/DOM elements may be used in one board at a
#: time (they mount where they live).
ReorderContent = ReactiveText | Component | DOMElement

#: Card content type parameter — a :class:`Reorder` board is generic over
#: what its cards contain; pass the concrete type to get typed ``items``
#: (``Reorder[Badge]``, ``Reorder[Text]``, …).
T = TypeVar("T", bound=ReorderContent)

#: Auto-generated root key prefix (``key=None`` boards get one so the
#: engine's "cursor inside this container" check works — the root itself
#: must be keyed).  Deliberately distinct from common card keys
#: (``reorder-1`` …), which would collide in the same DOM tree.
_KEY_PREFIX = "reorder-board-"

#: Next auto-generated root key number (per-process; board keys only need
#: to be unique within one page render).
_key_seq = 0

#: Next auto-generated CARD key number — bare components (e.g. a stack of
#: ``Card``s) get ``reorder-card-N`` keys so no explicit key is needed.
_card_key_seq = 0


class ReorderItem(Generic[T]):
    """One card in a :class:`Reorder` board.

    ``content`` is the card body — text (plain or reactive), a component,
    or a DOM element; ``key`` is the card's identity for ``order`` /
    ``drop`` payloads.  The wrapper is optional: bare content resolves a
    key from a keyed DOM element's own key, a plain-string label, or an
    auto-generated key (components like ``Card`` need none).  Cross-board
    moves need globally unique keys.
    """

    __slots__ = ("content", "key")

    def __init__(self, content: T, *, key: str | None = None) -> None:
        self.content: T = content
        self.key = key


def _px_half(size: str) -> float:
    """Half of a ``"<n>px"`` size — the insertion-side threshold the
    engine's encoded drop offset (0 or the full card size) is compared
    against."""
    if not size.endswith("px"):
        raise ValueError(f"Reorder: size must be a px value, got {size!r}")
    return float(size[:-2]) / 2


class Reorder(Component, Generic[T]):
    #: ``drop`` is wired internally (per card); Component.on() must not
    #: wire the root again or card drops would double-fire.
    _bound_events: frozenset[str] = frozenset({"drop"})

    #: Card key → the board that owns it, for cross-board drops (the drop
    #: arrives at the target board's card with the source's payload key;
    #: the target resolves the owning board here and moves the card).
    _board_by_key: ClassVar[dict[str, Reorder]] = {}

    def __init__(
        self,
        *items: ReorderItem[T] | T,
        direction: Literal["row", "column"] = "row",
        wrap: bool = True,
        gap: str = "8px",
        size: str = "72px",
        max_width: str | None = None,
        key: str | None = None,
    ) -> None:
        super().__init__()
        global _key_seq
        if key is None:
            _key_seq += 1
            key = f"{_KEY_PREFIX}{_key_seq}"
        self._direction = direction
        self._size = size
        self._half = _px_half(size)
        self._cards: list[Div] = []
        self._item_by_key: dict[str, ReorderItem] = {}
        self._root = Div(
            key=key,
            styles=Styles(
                display="flex",
                flex_direction=direction,
                flex_wrap="wrap" if wrap else "nowrap",
                gap=gap,
                padding="4px",
                max_width=max_width,
            ),
        )
        for item in items:
            self.add(item)

    # ---- public API ----

    def add(self, item: ReorderItem[T] | T) -> Self:
        """Append a card (chainable).

        Accepts a :class:`ReorderItem` or any card content — a plain or
        reactive string, a :class:`Component`, or a
        :class:`~neony.dom.DOMElement`.  Strings are wrapped as
        :class:`ReorderItem` (key = the label); keyed DOM elements keep
        their own key; everything else gets an auto-generated key, so a
        bare component (e.g. a stack of ``Card``s) needs no wrapper.
        """
        entry = item if isinstance(item, ReorderItem) else ReorderItem(item)  # type: ignore[type-var]
        key = entry.key
        if key is None:
            if isinstance(entry.content, DOMElement) and entry.content.key:
                key = entry.content.key
            elif isinstance(entry.content, str):
                key = entry.content
            else:
                # Bare component/DOM content: auto-key so `Reorder(Card(...),
                # Card(...))` just works.  Deterministic and unique per board.
                global _card_key_seq
                _card_key_seq += 1
                key = f"reorder-card-{_card_key_seq}"
        if key in self._item_by_key:
            raise ValueError(f"Reorder: duplicate card key {key!r}")
        entry.key = key  # persist the resolved identity
        card = self._build_card(entry, key)
        self._cards.append(card)
        self._root.container.append(card)
        self._item_by_key[key] = entry
        Reorder._board_by_key[key] = self
        return self

    def children(self, *items: ReorderItem[T] | T) -> Self:
        """Append several cards (chainable) — see :meth:`add`."""
        for item in items:
            self.add(item)
        return self

    @property
    def order(self) -> list[str]:
        """Card keys in render order."""
        return [c.key for c in self._cards]

    @property
    def items(self) -> list[ReorderItem[T]]:
        """All cards, in render order."""
        return [self._item_by_key[c.key] for c in self._cards]

    # ---- internals ----

    def _build_card(self, entry: ReorderItem[T], key: str, reuse_el: DOMElement | None = None) -> Div:
        """Create the draggable card element for *entry*.

        ``reuse_el`` (a card's content element handed over by another
        board) is attached as-is — components and DOM elements mount in
        exactly one place, so a cross-board move carries the element over
        instead of rebuilding it.
        """
        card = Div(
            key=key,
            drag_payload=key,
            styles=Styles(
                width=self._size if self._direction == "row" else None,
                height=self._size,
                border="1px solid var(--color-border)",
                border_radius="8px",
                background_color=stub.surface,
                display="flex",
                align_items="center",
                justify_content="center",
                padding="0 12px",
                cursor="grab",
                user_select="none",
            ),
            container=[],
        )
        content = entry.content
        if reuse_el is not None:
            card.container = [reuse_el]
        elif isinstance(content, (Signal, Computed)):
            card.bind_text(content)
        elif isinstance(content, str):
            card.container = [content]
        elif isinstance(content, Component):
            card.container = [content.build()]
        else:
            card.container = [content]
        card.on_drop(self._make_drop_handler(key))
        return card

    def _pop(self, key: str) -> tuple[ReorderItem[T], DOMElement | None]:
        """Remove the card *key* from this board; returns its item and its
        content element (if any) for the receiving board to reuse."""
        idx = next(i for i, c in enumerate(self._cards) if c.key == key)
        card = self._cards.pop(idx)
        item = self._item_by_key.pop(key)
        Reorder._board_by_key.pop(key, None)
        for i, child in enumerate(self._root.container):
            if child is card:
                self._root.container.pop(i)
                break
        reuse = card.container[0] if card.container and isinstance(card.container[0], DOMElement) else None
        return item, reuse

    def _insert(self, item: ReorderItem[T], reuse_el: DOMElement | None, target_key: str, before: bool) -> None:
        """Insert *item* into this board at *target_key*'s position (the
        same side the preview showed)."""
        key = item.key
        if key is None:
            raise ValueError("Reorder: cross-board item has no key")
        cards = self._cards
        target = next(c for c in cards if c.key == target_key)
        index = cards.index(target)
        insert_at = index if before else index + 1
        card = self._build_card(item, key, reuse_el)
        cards.insert(insert_at, card)
        self._root.container.insert(insert_at, card)
        self._item_by_key[key] = item
        Reorder._board_by_key[key] = self

    def _make_drop_handler(self, key: str):
        async def handler(event: DomEvent) -> None:
            dragged_key = event.drag_payload
            target_key = event.key
            if not dragged_key or dragged_key == target_key:
                return  # dropped on itself
            if self._direction == "row":
                insert_before = (event.offset_x or 0) < self._half  # left half
            else:
                insert_before = (event.offset_y or 0) < self._half  # upper half
            if dragged_key in self._item_by_key:
                # Same board: reorder internally.
                cards = self._cards
                try:
                    dragged = next(c for c in cards if c.key == dragged_key)
                    target = next(c for c in cards if c.key == target_key)
                except StopIteration:
                    return
                cards.remove(dragged)
                index = cards.index(target)
                cards.insert(index if insert_before else index + 1, dragged)
                self._root.container[:] = cards
            else:
                # Cross-board: the source card belongs to another board —
                # move the item over (the receiving board rebuilds its card
                # from the handed-off item).
                source = Reorder._board_by_key.get(dragged_key)
                if source is None or source is self:
                    return
                item, reuse = source._pop(dragged_key)
                self._insert(item, reuse, target_key, insert_before)
            event.value = self.order
            event.source = "user"
            await self._dispatch("drop", event)

        return handler
