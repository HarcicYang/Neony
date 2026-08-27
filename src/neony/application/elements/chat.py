"""Chat components — message bubbles and the centered system notice.

:class:`MessageBubble` renders one chat message in the QQ/Telegram style:
``from_me`` flips alignment (self → right, others → left) and the bubble
fill (self → accent, others → surface).  An optional :class:`Avatar` sits
on the message's own side, an optional sender ``name`` labels the bubble,
optional quick-action buttons sit below it and reveal on hover, and a
built-in :class:`Menu` opens on right-click (``menu_items=[]`` disables
it — the ``contextmenu`` event still reaches ``on_contextmenu``).

:class:`NoticeBubble` is the centered system message — a muted pill
("You joined the group") that centers itself in a flex message column.

The bubble's built-in menu is a ``position: fixed`` element embedded in
the bubble's DOM (hidden while closed).  Any ``backdrop-filter`` /
``transform`` ancestor would become its containing block in WebKit
(Dialog precedent) — keep chat panes on plain surfaces.
"""

from __future__ import annotations

import asyncio
import weakref
from collections.abc import Sequence
from typing import Literal, Self

from neony.application.theme import stub
from neony.dom import (
    Border,
    Color,
    Div,
    DOMElement,
    DomEvent,
    Span,
    Styles,
)
from neony.dom import Button as _ButtonElem
from neony.dom.reactive import Computed, Signal

from ..i18n import tr
from .avatar import Avatar
from .badge import Badge
from .base import Component, ReactiveText, _mount_text
from .icon import Icon
from .menu import Menu

_ROW = Styles(display="flex", align_items="flex-end", gap="10px", width="100%")

# Capped at 70% of the row so long messages wrap instead of stretching;
# the bubble inside fills the column and wraps at that cap.  relative:
# the hover quick-action row anchors to this column's box (absolute), so
# showing it never changes the bubble's footprint.
_COL = Styles(
    display="flex",
    flex_direction="column",
    gap="4px",
    max_width="70%",
    position="relative",
)

_NAME = Styles(display="inline-flex", font_size="12px", color=stub.text_secondary, padding="0 4px")
_NAME_HIDDEN = _NAME.model_copy(update={"display": "none"})

_BUBBLE = Styles(
    max_width="100%",
    padding="10px 14px",
    border_radius="16px",
    font_size="14px",
    line_height="1.45",
    word_break="break-word",
)

# Asymmetric corner radius — the corner toward the avatar is squared off,
# the classic chat-bubble tail substitute.
_BUBBLE_ME = Styles(
    background_color=stub.accent,
    color=Color(name="white"),
    border_radius="16px 16px 4px 16px",
)
_BUBBLE_OTHER = Styles(
    background_color=stub.surface_raised,
    color=stub.text_primary,
    border_radius="16px 16px 16px 4px",
)

# Hover-revealed quick actions, positioned just below the bubble.  Out of
# flow (absolute) so showing them never changes the row's height — they
# overlay the message below instead of pushing it.
# A short grace period bridges the small gap between a bubble and its
# absolutely positioned action row without making a real leave feel sticky.
_ACTIONS_HIDE_DELAY = 0.16

_ACTIONS = Styles(
    position="absolute",
    top="calc(100% + 2px)",
    display="none",
    gap="4px",
    z_index="10",
)
_ACTION = Styles(
    display="flex",
    align_items="center",
    justify_content="center",
    padding="4px 8px",
    border="none",
    border_radius="6px",
    background_color=Color(name="transparent"),
    color=stub.text_secondary,
    font_size="12px",
    cursor="pointer",
)

# One action row may be visible in each mounted DOM tree.  This is scoped by
# root rather than module-wide so independent application windows never affect
# one another.  The weak references also avoid retaining rebuilt message lists.
_MESSAGE_ACTION_OWNERS: dict[int, tuple[weakref.ReferenceType, weakref.ReferenceType]] = {}


def _default_menu() -> tuple[tuple[str, ReactiveText], ...]:
    """The built-in right-click menu items — live ``tr`` labels so the
    menu follows the active language.  ``Menu`` mounts each label on a
    child span (via :func:`_mount_text`), so a ``TrRef`` re-renders on
    :func:`set_language` without rebuilding the menu."""
    return (("copy", tr.common.copy_text), ("delete", tr.common.delete))


_NOTICE = Styles(
    display="inline-flex",
    align_self="center",
    max_width="80%",
    margin="6px auto",
    padding="5px 12px",
    border_radius="12px",
    background_color=stub.surface_glass_bg,
    border=Border(width="1px", color=stub.border_glass),
    color=stub.text_secondary,
    font_size="12px",
    line_height="1.4",
)


def _merge(base: Styles, overrides: Styles) -> Styles:
    """Base styles with the overrides' set fields applied (raw values, so
    nested Color / Border models survive — the Tooltip precedent)."""
    return base.model_copy(update={k: getattr(overrides, k) for k in overrides.model_fields_set})


class MessageBubble(Component):
    #: Wired internally; ``change`` re-dispatches the built-in menu's
    #: selection, ``click`` routes the quick-action buttons.
    _bound_events: frozenset[str] = frozenset({"change", "click", "contextmenu", "mouseover", "mouseout"})

    """One chat message — QQ/Telegram style.

    - ``from_me`` — self-messages sit right with an accent fill; other
      people's sit left on the raised surface
    - ``avatar`` — an optional :class:`Avatar` on the message's own side
      (built on construction)
    - ``name`` — optional sender label above the bubble
    - ``actions`` — optional quick-action buttons below the bubble
      (``(value, label)`` / ``str`` → text button, :class:`Icon` →
      icon button); hidden until the message is hovered
    - ``menu_items`` — the built-in right-click :class:`Menu` items
      (default Copy / Delete; ``[]`` disables the menu, ``on_contextmenu``
      still fires)
    - ``on_change(fn)`` — a menu selection, ``event.value`` is the value
    - ``on_action(fn)`` — a quick-action click, called with the value
    """

    def __init__(
        self,
        text: ReactiveText = "",
        *,
        from_me: bool = False,
        name: str | None = None,
        avatar: Avatar | None = None,
        content: Component | DOMElement | None = None,
        actions: Sequence[ReactiveText | tuple[str, ReactiveText] | Icon] = (),
        menu_items: Sequence[ReactiveText | tuple[str, ReactiveText]] | None = None,
        actions_placement: Literal["below", "beside"] = "below",
        action_size: str = "24px",
        name_badge: Badge | None = None,
        white_space: str = "normal",
    ) -> None:
        super().__init__()
        self._text = text
        self._name = name
        self._content = content
        self._from_me = from_me
        self._placement = actions_placement
        self._action_size = action_size
        self._white_space = white_space
        self._action_by_key: dict[str, str] = {}
        self._actions_shown = False
        self._actions_hide_task: asyncio.Task | None = None

        self._menu: Menu | None = None
        if menu_items is None:
            menu_items = _default_menu()
        if menu_items:
            self._menu = Menu(*menu_items)
            self._menu.on_change(self._on_menu_change)

        if avatar is not None:
            self._avatar_el: DOMElement | None = avatar.build()
        else:
            self._avatar_el = None

        self._name_badge_el: DOMElement | None = name_badge.build() if name_badge is not None else None
        name_styles = _NAME if name else _NAME_HIDDEN
        name_children: list[DOMElement | str]
        if self._name_badge_el is not None:
            # Reactive mode forbids mixing strings and elements inside one
            # node; the label therefore gets its own element beside the badge.
            name_children = [Span(container=[name or ""]), self._name_badge_el]
            name_styles = name_styles.model_copy(update={"gap": "4px"})
        else:
            name_children = [name or ""]
        self._name_span = Span(container=name_children, styles=name_styles)
        self._bubble = Div(styles=_BUBBLE, container=[])
        # Reactive text (Signal/Computed, e.g. ``tr.chat.other_msg``) binds
        # live; a plain str is mounted directly into the bubble.
        if content is None:
            _mount_text(self._bubble, text)
        else:
            content_el: DOMElement = content.build() if isinstance(content, Component) else content
            # Plain-list assignment bypasses _Children and leaves the
            # content subtree's _parent unset — eval-js walks (media play,
            # clipboard, scroll) would stop at the bubble and silently drop.
            self._bubble.container.clear()
            self._bubble.container.append(content_el)
        self._actions = Div(styles=_ACTIONS, container=[])
        self._col = Div(styles=_COL, container=[self._name_span, self._bubble, self._actions])

        for entry in actions:
            self._add_action(entry)

        self._root = Div(styles=_ROW, container=[])
        # Hover / right-click from inner elements (bubble text, action
        # buttons) must reach the row's handlers.
        self._root.bubble_events = True
        self._rebuild_row()
        if actions:
            self._root.args = {
                **self._root.args,
                "data-neony-message-actions": self._actions.key,
                "data-neony-overlay-group": "message-actions",
            }

        self._apply_side()
        self._bind(self._root, "mouseover")
        self._bind(self._root, "mouseout")
        self._bind(self._root, "contextmenu")

    # ---- state ----

    @property
    def text(self) -> str:
        return self._text() if isinstance(self._text, (Signal, Computed)) else self._text

    @text.setter
    def text(self, value: ReactiveText) -> None:
        self._text = value
        if self._content is None:
            self._bubble.container = []
            _mount_text(self._bubble, value)

    @property
    def name(self) -> str | None:
        return self._name

    @name.setter
    def name(self, value: str | None) -> None:
        self._name = value
        if self._name_badge_el is not None:
            self._name_span.container.clear()
            self._name_span.container.extend([Span(container=[value or ""]), self._name_badge_el])
        else:
            self._name_span.container.clear()
            self._name_span.container.append(value or "")
        self._name_span.styles = _NAME if value else _NAME_HIDDEN
        if self._name_badge_el is not None:
            self._name_span.styles = self._name_span.styles.model_copy(update={"gap": "4px"})

    @property
    def from_me(self) -> bool:
        return self._from_me

    @from_me.setter
    def from_me(self, value: bool) -> None:
        if value == self._from_me:
            return
        self._from_me = value
        self._rebuild_row()
        self._apply_side()

    # ---- public API ----

    def on_action(self, fn) -> Self:
        """Register a callback fired when a quick-action button is
        clicked (called with the action's value)."""
        return self.on("action", fn)

    @property
    def content(self) -> DOMElement | None:
        """The current custom content element, or ``None`` for text."""
        child = self._bubble.container[0] if self._bubble.container else None
        return child if isinstance(child, DOMElement) else None

    def set_content(self, child: Component | DOMElement) -> Self:
        """Replace the bubble's custom content element."""
        self._content = child
        self._bubble.container.clear()
        self._bubble.container.append(child.build() if isinstance(child, Component) else child)
        return self

    @property
    def actions_visible(self) -> bool:
        """True while this bubble's quick actions are shown."""
        return self._actions_shown

    def show_actions(self) -> Self:
        """Reveal the quick actions, claiming this row's action owner."""
        self._claim_actions()
        return self

    def hide_actions(self) -> Self:
        """Hide the quick actions immediately when this bubble owns them."""
        self._finish_actions_release()
        return self

    def action_elements(self) -> tuple[DOMElement, ...]:
        """The mounted quick-action buttons, in display order."""
        return tuple(el for el in self._actions.container if isinstance(el, DOMElement))

    def action_values(self) -> tuple[str, ...]:
        """The quick-action values, in display order."""
        return tuple(self._action_by_key[el.key] for el in self.action_elements())

    @property
    def overlay_slot(self) -> DOMElement:
        """The bubble's positioned column for anchoring overlays above it."""
        return self._col

    # ---- internals ----

    def _rebuild_row(self) -> None:
        """Lay the row out as ``[avatar?, col]`` for others or
        ``[col, avatar?]`` for self (avatar sits on the message's side),
        keeping the fixed menu overlay mounted."""
        menu_root = self._menu._root if self._menu is not None else None
        self._root.container.clear()
        if self._from_me:
            self._root.container.append(self._col)
            if self._avatar_el is not None:
                self._root.container.append(self._avatar_el)
        else:
            if self._avatar_el is not None:
                self._root.container.append(self._avatar_el)
            self._root.container.append(self._col)
        if menu_root is not None:
            self._root.container.append(menu_root)

    def _apply_side(self) -> None:
        end = "flex-end" if self._from_me else "flex-start"
        self._root.styles = self._root.styles.model_copy(update={"justify_content": end})
        self._col.styles = self._col.styles.model_copy(update={"align_items": end})
        side = _BUBBLE_ME if self._from_me else _BUBBLE_OTHER
        self._bubble.styles = _merge(_BUBBLE, side)
        if self._white_space != "normal":
            self._bubble.styles = self._bubble.styles.model_copy(update={"white_space": self._white_space})
        # The hover action row anchors to the side of the bubble it hangs
        # below: right edge for self-messages, left edge for others.
        action_update: dict[str, object] = {
            "justify_content": end,
            "left": "0" if not self._from_me else None,
            "right": "0" if self._from_me else None,
        }
        if self._placement == "beside":
            action_update.update(
                {
                    "top": "50%",
                    "transform": "translateY(-50%)",
                    "left": "calc(100% + 6px)" if not self._from_me else None,
                    "right": "calc(100% + 6px)" if self._from_me else None,
                }
            )
        else:
            action_update.update({"top": "calc(100% + 2px)", "transform": None})
        self._actions.styles = self._actions.styles.model_copy(update=action_update)

    def _add_action(self, entry: ReactiveText | tuple[str, ReactiveText] | Icon) -> None:
        if isinstance(entry, Icon):
            value: str = entry.src
            btn_content: DOMElement | ReactiveText = entry.render("14px")
        elif isinstance(entry, tuple):
            value, label = entry
            btn_content = label
        elif isinstance(entry, str):
            # A plain-string entry doubles as its own value — a static key,
            # so a reactive label must come as a (value, label) tuple.
            value = label = entry
            btn_content = label
        else:
            raise ValueError("MessageBubble.actions: a reactive label needs a (value, label) tuple")
        action_styles = _ACTION
        if self._action_size:
            action_styles = action_styles.model_copy(
                update={
                    "width": self._action_size,
                    "height": self._action_size,
                    "padding": "0",
                    "appearance": "none",
                    "line_height": "1",
                }
            )
        # A reactive label (a ``tr`` ref) rides a child span so it can
        # re-render on language switch; an Icon or a plain str mounts
        # directly into the button.
        if isinstance(btn_content, (Signal, Computed)):
            label_span = Span(container=[])
            label_span.styles = label_span.styles.model_copy(update={"pointer_events": "none"})
            _mount_text(label_span, btn_content)
            btn = _ButtonElem(type="button", container=[label_span], styles=action_styles)
            label_span.bubble_events = True  # label-span clicks reach the row
        else:
            if isinstance(btn_content, DOMElement):
                btn_content.styles = btn_content.styles.model_copy(update={"pointer_events": "none"})
            btn = _ButtonElem(type="button", container=[btn_content], styles=action_styles)
        self._action_by_key[btn.key] = value
        self._bind(btn, "click")
        self._actions.container.append(btn)

    def _actions_scope(self) -> object:
        """Return this bubble's mounted tree root for owner isolation."""
        node = self._root
        while node._parent is not None:
            node = node._parent
        return node

    def _set_actions_visible(self, visible: bool) -> None:
        if visible == self._actions_shown:
            return
        self._actions_shown = visible
        self._actions.styles = self._actions.styles.model_copy(update={"display": "flex" if visible else "none"})

    def _actions_entry(self) -> tuple[object, weakref.ReferenceType[MessageBubble] | None]:
        """Return this tree's live scope and its current action owner."""
        scope = self._actions_scope()
        entry = _MESSAGE_ACTION_OWNERS.get(id(scope))
        if entry is None or entry[0]() is not scope:
            return scope, None
        return scope, entry[1]

    def _cancel_actions_hide(self) -> None:
        if self._actions_hide_task is not None:
            self._actions_hide_task.cancel()
            self._actions_hide_task = None

    def _claim_actions(self) -> None:
        self._cancel_actions_hide()
        scope, previous_ref = self._actions_entry()
        previous = previous_ref() if previous_ref is not None else None
        if previous is not None and previous is not self:
            previous._cancel_actions_hide()
            previous._set_actions_visible(False)
        _MESSAGE_ACTION_OWNERS[id(scope)] = (weakref.ref(scope), weakref.ref(self))
        self._set_actions_visible(True)

    def _release_actions(self) -> None:
        self._cancel_actions_hide()
        try:
            self._actions_hide_task = asyncio.create_task(self._hide_actions_after_delay())
        except RuntimeError:
            # Direct programmatic/unit-test calls without a running loop keep
            # their deterministic immediate close semantics.
            self._finish_actions_release()

    async def _hide_actions_after_delay(self) -> None:
        try:
            await asyncio.sleep(_ACTIONS_HIDE_DELAY)
            self._finish_actions_release()
        except asyncio.CancelledError:
            return
        finally:
            if self._actions_hide_task is asyncio.current_task():
                self._actions_hide_task = None

    def _finish_actions_release(self) -> None:
        scope, current_ref = self._actions_entry()
        if current_ref is not None and current_ref() is self:
            del _MESSAGE_ACTION_OWNERS[id(scope)]
            self._set_actions_visible(False)

    def _related_inside(self, key: str | None) -> bool:
        """True when *key* belongs to the row's subtree — the pointer is
        still inside, so no hover enter/leave fires (Tooltip precedent)."""
        if key is None:
            return False
        stack = [self._root]
        while stack:
            el = stack.pop()
            if el.key == key:
                return True
            stack.extend(c for c in el.container if isinstance(c, DOMElement))
        return False

    async def _on_menu_change(self, event: DomEvent) -> None:
        await self._dispatch("change", event)

    # ---- events ----

    async def _on_event(self, event_type: str, event: DomEvent) -> None:
        if event_type == "mouseover":
            if not self._related_inside(event.related_key):
                self._claim_actions()
        elif event_type == "mouseout":
            if not self._related_inside(event.related_key):
                self._release_actions()
        elif event_type == "contextmenu":
            if self._menu is not None:
                self._menu.open_at(event.x or 0, event.y or 0)
        elif event_type == "click":
            value = self._action_by_key.get(event.key)
            if value is not None:
                self._dispatch_pseudo("action", value)
                return  # action clicks are not forwarded as generic clicks
        await self._dispatch(event_type, event)


class NoticeBubble(Component):
    """A centered system message (e.g. "You joined the group").

    Renders as a muted pill that centers itself in a flex message
    column (``align-self: center``); ``text`` is the message, or pass
    ``content`` for a custom element.

    ``text`` accepts a reactive source (Signal/Computed, e.g. a ``tr``
    ref wrapped in a ``Computed``) so language switches update it live;
    plain strings are set directly (see :func:`_mount_text`).
    """

    def __init__(self, text: ReactiveText = "", *, content: Component | DOMElement | None = None) -> None:
        super().__init__()
        self._text = text
        self._content = content
        if content is not None:
            children: list[DOMElement | str] = [content.build() if isinstance(content, Component) else content]
            self._root = Div(styles=_NOTICE, container=children)
        else:
            self._root = Div(styles=_NOTICE, container=[])
            _mount_text(self._root, text)

    @property
    def text(self) -> str:
        if isinstance(self._text, (Signal, Computed)):
            return self._text()
        return self._text

    @text.setter
    def text(self, value: str) -> None:
        self._text = value
        if self._content is None:
            self._root.container = [value]
