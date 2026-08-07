"""Internal panel-host machinery: a scrollable column of slot Divs where
exactly one slot is visible at a time.  Owns the visibility toggle (and
the replayed entrance animation) that keeps pane roots cached and
mounted — switching never moves DOM elements, so pane state (input
values, scroll offsets) survives switches.

Used by :class:`Sidebar` for its content panes.  TODO(R2 Shell): Tabs
owns the same machinery inline today; refactor it onto this host when
the Shell lands so all three share one implementation.
"""

from __future__ import annotations

from neony.dom import Animation, Div, DOMElement, Styles

# Column that fills the space left by the rail: grows, never overflows
# the window (min-height:0), scrolls when a pane is taller than it.
_HOST = Styles(
    display="flex",
    flex_direction="column",
    flex_grow="1",
    min_width="0",
    min_height="0",
    overflow="auto",
)

_SLOT_HIDDEN = Styles(display="none", width="100%")

# Entering panes fade + slide up from the built-in "neony-rise-in"
# keyframe (injected by the app with every window).  The switch from
# _SLOT_HIDDEN (no animation) to _SLOT_ACTIVE changes the animation
# value, so the browser replays it on every activation.
# flex_grow makes the slot fill the host's remaining height — panes that
# stretch themselves (GlassPanel grow=True → height:100%) need a
# definite parent height to resolve against.
_SLOT_ACTIVE = Styles(
    display="flex",
    flex_direction="column",
    width="100%",
    min_height="0",
    flex_grow="1",
    animation=Animation(name="neony-rise-in", duration="0.25s", timing="ease-out"),
)


class _PanelHost:
    """Scrollable column of slots; ``set_active(index)`` shows exactly
    one.  ``index`` is a plain int — callers map their own selection
    model (key → slot index) onto it."""

    def __init__(self) -> None:
        self._root = Div(styles=_HOST)
        self._slots: list[Div] = []
        self._active: int = -1

    @property
    def root(self) -> Div:
        """The host container; mount this in the parent layout."""
        return self._root

    @property
    def slots(self) -> list[Div]:
        return list(self._slots)

    def add(self, element: DOMElement) -> Div:
        """Wrap *element* in a hidden slot and append it (returns the slot)."""
        slot = Div(styles=_SLOT_HIDDEN, container=[element])
        self._slots.append(slot)
        self._root.container.append(slot)
        self._apply_visibility()
        return slot

    def set_active(self, index: int) -> None:
        """Show slot *index*, hide the rest.  Raises ``IndexError`` when
        out of range (``-1`` hides everything)."""
        if not -1 <= index < len(self._slots):
            raise IndexError(f"_PanelHost.set_active: index {index} out of range")
        self._active = index
        self._apply_visibility()

    def _apply_visibility(self) -> None:
        for i, slot in enumerate(self._slots):
            slot.styles = _SLOT_ACTIVE if i == self._active else _SLOT_HIDDEN
