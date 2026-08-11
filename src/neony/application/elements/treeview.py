"""Tree component — a collapsible navigation tree with a content host.

A :class:`Tree` renders an arbitrary-depth hierarchy of :class:`TreeNode`
entries in a left rail and owns a content host on the right (the same
``_PanelHost`` machinery :class:`Sidebar` uses).  Clicking a **leaf**
node (a node with a ``panel``) shows its panel in the host; clicking a
**branch** (a node with ``children``) only expands / collapses its
children.  Several branches can be open at once.

:class:`TreeNode` supports a fluent builder form so trees read well::

    Tree(
        TreeNode("Home", key="home").panel(home_panel),
        TreeNode("Forms", expanded=True).children(
            TreeNode("Inputs", key="inputs").panel(inputs_panel),
            TreeNode("Checks", key="checks").panel(checks_panel),
        ),
    ).active_key = "home"

Selection is single-valued (exactly one leaf is shown at a time), so
``selected_key`` / ``bind_selected`` work like :class:`Sidebar` — unlike
the multi-open :class:`Accordion`.  Only the ``display`` property
switches (plus the replayed ``neony-drop-in`` entrance animation), so
this is pure Python — no JS-layer involvement.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from typing import Any, Self

from neony.application.theme import stub
from neony.dom import Animation, Color, Div, DOMElement, DomEvent, Span, Styles, Transition, calc

from .. import shortcuts
from ._panels import _PanelHost
from .base import Component
from .icon import Icon

# ---- node rows ----

_ROW_BASE = Styles(
    display="flex",
    align_items="center",
    gap="8px",
    padding="12px 16px",
    border_radius="8px",
    font_size="14px",
    cursor="pointer",
    background_color=Color(name="transparent"),
    color=stub.text_secondary,
    white_space="nowrap",
    overflow="hidden",
    text_overflow="ellipsis",
    user_select="none",
    transition=Transition(property="background-color", duration="0.15s", timing="ease"),
)

_ROW_ACTIVE = _ROW_BASE.model_copy(
    update={
        "background_color": stub.surface,
        "color": stub.text_primary,
    }
)

_BRANCH_ROW = _ROW_BASE.model_copy(update={"font_weight": "600"})

# The branch chevron (▶/▼) — rotates on open.
_CHEVRON = Styles(
    display="inline-flex",
    font_size="11px",
    width="14px",
    flex_shrink="0",
    transition=Transition(property="transform", duration="0.15s", timing="ease"),
)
_CHEVRON_OPEN = _CHEVRON.model_copy(update={"transform": "rotate(90deg)"})

# Expanding a branch flips display none→flex, which replays neony-drop-in
# (mirrors accordion _CONTENT_VISIBLE).
_CHILDREN_HIDDEN = Styles(display="none")
_CHILDREN_VISIBLE = Styles(
    display="flex",
    flex_direction="column",
    gap="2px",
    animation=Animation(name="neony-drop-in", duration="0.2s", timing="ease-out"),
)

_INDENT = "16px"

# Tree root = the rail itself: a transparent scroll column (accordion
# styling — rounded rows only, no rectangular chrome around them).  The
# host fills the remaining stage space via flex, so the tree is bounded
# by the parent height and scrolls internally instead of growing the
# page (mirrors Sidebar's split without the rail's own chrome).
#
# NOTE on sizing: the rail sits in a row-direction flex root, so its
# width is fixed by `width` + flex_shrink:0 (flex-grow would swallow the
# free space and make the rail resize with the window); it anchors to
# the root's definite height via height:100% so overflow-y:auto clamps
# and the rail scrolls internally instead of growing the page when a
# branch expands.
_RAIL = Styles(
    display="flex",
    flex_direction="column",
    gap="2px",
    # Vertical padding reserves a breathing rim at top/bottom.  The edge
    # fade is now owned and applied dynamically by the JS scroll indicator
    # (data-neony-scroll, derived from overflow_y below), so this no longer
    # has to match a static mask width — it just keeps the first/last rows
    # off the rail rim.
    padding="36px 0",
    height="100%",
    min_height="0",
    overflow_y="auto",
    overflow_x="hidden",
)


def _attr_roles(role: str, **attrs: str) -> dict[str, str]:
    """ARIA attrs for a node row — internal only (never user-facing)."""
    return {"role": role, **attrs}


class TreeNode:
    """One node in a :class:`Tree` — a **branch** (with ``children``) or
    a **leaf** (with a ``panel``).  Never both: a node with a panel and
    children raises ``ValueError``.

    Fluent builders::

        TreeNode("Home", key="home").panel(home_panel)
        TreeNode("Forms").children(
            TreeNode("Inputs", key="inputs").panel(inputs_panel),
            TreeNode("Checks", key="checks").panel(checks_panel),
        )

    ``label`` is the entry text (first positional argument); ``key``
    defaults to a random id so labels never collide; ``icon`` is an
    optional :class:`Icon` shown before the label; ``expanded`` sets the
    initial expanded state of a branch; ``shortcut`` is an optional
    window-level combo for a leaf (same forms as ``Page.on_shortcut``),
    collected via :meth:`Tree.shortcuts`.
    """

    __slots__ = ("_children", "_depth", "_panel", "expanded", "icon", "key", "label", "shortcut")

    def __init__(
        self,
        label: str = "",
        *,
        key: str | None = None,
        icon: Icon | None = None,
        panel: Component | DOMElement | None = None,
        expanded: bool | None = None,
        children: list[TreeNode] | None = None,
        shortcut: str | dict[str, str] | None = None,
    ) -> None:
        if panel is not None and children:
            raise ValueError("TreeNode: a node cannot have both a panel and children")
        self.label = label
        self.key = key
        self.icon = icon
        # expanded: None = follow the Tree's policy (expanded_branches);
        # True/False = the caller's explicit initial state.
        self.expanded = expanded
        self.shortcut = shortcut
        self._panel = panel
        self._children = list(children) if children else []
        self._depth = 0  # set by Tree on registration

    # ---- fluent builders (return self) ----

    def panel(self, panel: Component | DOMElement) -> TreeNode:
        """Attach a content panel (leaf node) — chainable."""
        if self._children:
            raise ValueError("TreeNode: a node with children cannot carry a panel")
        self._panel = panel
        return self

    def children(self, *nodes: TreeNode) -> TreeNode:
        """Attach child nodes (branch node) — chainable."""
        if self._panel is not None:
            raise ValueError("TreeNode: a node with a panel cannot carry children")
        self._children = list(nodes)
        return self

    def key_(self, key: str) -> TreeNode:
        """Set the node key explicitly — chainable."""
        self.key = key
        return self

    # ---- read access ----

    @property
    def is_branch(self) -> bool:
        return bool(self._children)

    @property
    def is_leaf(self) -> bool:
        return self._panel is not None

    @property
    def resolved_key(self) -> str:
        """The key — defaults to a stable random id, resolved once."""
        if self.key is None:
            self.key = uuid.uuid4().hex
        return self.key


class Tree(Component):
    """Left navigation rail of :class:`TreeNode` entries + a right content
    host; exactly one leaf's panel is visible at a time.

    Usage::

        tree = Tree(
            TreeNode("Home", key="home").panel(home_panel),
            TreeNode("Forms", expanded=True).children(
                TreeNode("Inputs", key="inputs").panel(inputs_panel),
                TreeNode("Checks", key="checks").panel(checks_panel),
            ),
        )
        tree.on_change(lambda e: print(e.value))  # leaf key
        tree.selected_key = "inputs"  # programmatic, no callback

    ``width`` is the rail width (the host adapts to the rest).  With
    ``expanded_branches=True`` (default) top-level branches start
    expanded.  Rows mirror the :class:`Accordion` header styling —
    rounded, transparent, with the same chevron rotation — and the rail
    is chrome-free: no wrapper box, no background, no divider.

    Mounting contract: the tree is self-bounding — it fills the height
    its flex parent allocates and scrolls its rail internally.  It must
    be mounted in a flex container with a *definite* height (e.g. a
    ``VStack(..., grow=1)`` or ``GlassPanel(grow=True)``); a bare block
    parent with auto height gives it nothing to bound against and the
    tree pushes the page open instead of scrolling.
    """

    def __init__(
        self,
        *nodes: TreeNode,
        width: str = "220px",
        expanded_branches: bool = True,
        active_key: str | None = None,
        fallback_panel: Component | DOMElement | None = None,
        edge_fade: bool = True,
    ) -> None:
        super().__init__()
        self._width = width
        self._expanded_branches = expanded_branches
        self._leaves: list[TreeNode] = []  # registration order = host slots
        self._leaf_keys: list[str] = []
        self._nodes: list[TreeNode] = []  # all nodes, depth-first
        self._row_by_key: dict[str, Div] = {}
        self._children_cols: dict[str, Div] = {}  # branch key -> children column
        self._selected_key: str | None = None
        self._host = _PanelHost()
        self._fallback_slot: Div | None = None
        self._shortcuts: list[tuple[str | dict[str, str], Callable[[], Any]]] = []
        # Breathe around the host's content: an inner margin so leaf
        # panels don't hug the rail border / window edge.
        self._host.root.styles = self._host.root.styles.model_copy(update={"padding": "8px 24px"})

        if fallback_panel is not None:
            # Shown when selection is None (see selected_key setter).
            fallback_el = fallback_panel.build() if isinstance(fallback_panel, Component) else fallback_panel
            self._fallback_slot = self._host.add(fallback_el)

        rail_styles = _RAIL.model_copy(update={"width": width, "flex_shrink": "0"})
        # scroll_indicator (driven by edge_fade) lets the JS engine derive
        # the data-neony-scroll marker from overflow_y and build the custom
        # thumb + dynamic edge fade on the rail.  The mask itself is no
        # longer set in Python — the JS engine owns it dynamically.
        self._rail = Div(styles=rail_styles, scroll_indicator=edge_fade)

        # Root = rail (fixed width) + host (absorbs the rest) side by
        # side.  flex-grow:1 + min-height:0 make the tree consume the
        # space its flex parent allocates (and shrink to 0 when there's
        # none) instead of growing the page.  flex-basis:0 (not the
        # auto default) keeps the tree's height pinned to the parent's
        # allocation — without it the root's basis = max(rail, host
        # panel) intrinsic height, so switching to a taller pane would
        # grow the tree and shift the rows.  No height:100% here —
        # combined with flex-grow it would total more than the parent
        # (100% basis + grown space) and overlap siblings; the rail gets
        # its definite height via height:100% instead.
        self._root = Div(
            styles=Styles(
                display="flex",
                flex_direction="row",
                flex_grow="1",
                flex_basis="0",
                min_height="0",
            ),
            container=[self._rail, self._host.root],
        )

        for node in nodes:
            self.add(node)
        if active_key is not None:
            self.selected_key = active_key

    # ---- public API ----

    def add(self, node: TreeNode) -> Self:
        """Append a top-level :class:`TreeNode` (chainable)."""
        # Resolve a branch's initial expansion: the caller's explicit
        # expanded flag wins; otherwise top-level branches follow the
        # expanded_branches policy.
        if node.is_branch and node.expanded is None:
            node.expanded = self._expanded_branches
        row, col = self._render_node(node, depth=0)
        self._rail.container.append(row)
        if col is not None:
            self._rail.container.append(col)
        return self

    def children(self, *nodes: TreeNode) -> Self:
        """Append several top-level nodes (chainable)."""
        for node in nodes:
            self.add(node)
        return self

    @property
    def items(self) -> list[TreeNode]:
        """All nodes, depth-first, in render order."""
        return list(self._nodes)

    @property
    def selected_key(self) -> str | None:
        return self._selected_key

    @selected_key.setter
    def selected_key(self, value: str | None) -> None:
        if value is None and self._fallback_slot is None:
            raise ValueError("Tree.selected_key: None needs a fallback_panel to select nothing")
        if value is not None and value not in self._leaf_keys:
            raise ValueError(f"Tree.selected_key: unknown leaf key {value!r}")
        self._selected_key = value
        for node in self._leaves:
            self._apply_leaf_active(node)
        self._sync_host()
        self._mirror_selected(value)

    @property
    def active_key(self) -> str | None:
        """Deprecated alias of :attr:`selected_key`."""
        return self._selected_key

    @active_key.setter
    def active_key(self, value: str | None) -> None:
        self.selected_key = value

    def shortcuts(self) -> list[tuple[str | dict[str, str], Callable[[], Any]]]:
        """``(combo, handler)`` pairs for leaves that declared one — wire
        them with ``Page.on_shortcut``."""
        return list(self._shortcuts)

    # ---- internals: render ----

    def _render_node(self, node: TreeNode, *, depth: int) -> tuple[Div, Div | None]:
        """Render *node* into ``(row, children_column)`` — branches return
        both (the column follows the row as its sibling), leaves return
        ``(row, None)``.  No wrapper element: rows sit directly in the
        rail with their own rounded corners (accordion-style)."""
        node._depth = depth
        self._nodes.append(node)
        if node.is_branch:
            return self._render_branch(node, depth=depth)
        return self._render_leaf(node, depth=depth), None

    def _render_branch(self, node: TreeNode, *, depth: int) -> tuple[Div, Div]:
        # Branch rows always carry the chevron Span, so the label must be
        # element-only too (reactive mode forbids mixing).
        label: list[DOMElement | str]
        if node.icon is not None:
            label = [node.icon.render("14px"), Span(container=[node.label])]
        else:
            label = [Span(container=[node.label])]
        row = Div(
            container=[
                self._chevron_span(node),
                *label,
            ],
            styles=_BRANCH_ROW.model_copy(update={"padding_left": calc(f"16px + {depth} * {_INDENT}")}),
            args=_attr_roles("treeitem", **{"aria-expanded": "true" if node.expanded else "false", "tabindex": "0"}),
        )
        # Clicks land on the chevron / icon / label spans — bubble them
        # to this row (mirrors SidebarItem).
        row.bubble_events = True
        row.on_click(self._make_branch_handler(node, row))
        row.key = f"branch:{node.resolved_key}"
        self._row_by_key[node.resolved_key] = row
        row.on("keydown", self._make_keydown_handler(node, row))

        # Children column is PRE-BUILT regardless of expanded state — toggling
        # only switches display, so subtree state (selection, expansion) stays
        # stable and no DOM is rebuilt (mirrors _PanelHost's approach).
        col = Div(styles=_CHILDREN_VISIBLE if node.expanded else _CHILDREN_HIDDEN)
        self._children_cols[node.resolved_key] = col
        for child in node._children:
            child_row, child_col = self._render_node(child, depth=depth + 1)
            col.container.append(child_row)
            if child_col is not None:
                col.container.append(child_col)
        return row, col

    def _render_leaf(self, node: TreeNode, *, depth: int) -> Div:
        active = node.resolved_key == self._selected_key
        row = Div(
            container=self._label_content(node),
            styles=(_ROW_ACTIVE if active else _ROW_BASE).model_copy(
                update={"padding_left": calc(f"16px + {depth} * {_INDENT}")}
            ),
            args=_attr_roles("treeitem", **{"aria-selected": "true" if active else "false", "tabindex": "0"}),
        )
        # Clicks land on the icon / label spans — bubble them to this row
        # (mirrors SidebarItem).
        row.bubble_events = True
        row.on_click(self._make_leaf_handler(node, row))
        row.key = f"leaf:{node.resolved_key}"
        self._row_by_key[node.resolved_key] = row
        row.on("keydown", self._make_keydown_handler(node, row))

        # Register into the host slot.
        if node._panel is None:
            raise ValueError(f"Tree: leaf node {node.resolved_key!r} has no panel")
        panel_el = node._panel.build() if isinstance(node._panel, Component) else node._panel
        self._host.add(panel_el)
        self._leaves.append(node)
        self._leaf_keys.append(node.resolved_key)
        if node.shortcut is not None:
            shortcuts.parse_combo(shortcuts.resolve_combo(node.shortcut))
            self._shortcuts.append((node.shortcut, self._make_shortcut_handler(node.resolved_key)))
        return row

    def _chevron_span(self, node: TreeNode) -> Span:
        return Span(
            container=["▶"],
            styles=_CHEVRON_OPEN if node.expanded else _CHEVRON,
        )

    def _label_content(self, node: TreeNode) -> list[DOMElement | str]:
        """The label row children: an optional Icon span + the label text
        (element-only when an icon is present — reactive mode forbids
        mixing)."""
        if node.icon is not None:
            return [node.icon.render("14px"), Span(container=[node.label])]
        return [node.label]

    # ---- internals: events ----

    def _make_keydown_handler(self, node: TreeNode, row: Div):
        async def handler(event: DomEvent) -> None:
            key = event.value  # the pressed key rides on event.value
            if key == "Enter" or key == " ":
                if node.is_branch:
                    self._toggle_branch(node)
                else:
                    self.selected_key = node.resolved_key
                event.value = node.resolved_key
                event.source = "user"
                await self._dispatch("change", event)
            elif key == "ArrowDown":
                self._move_focus(1, node, row)
            elif key == "ArrowUp":
                self._move_focus(-1, node, row)
            elif (key == "ArrowRight" and node.is_branch and not node.expanded) or (
                key == "ArrowLeft" and node.is_branch and node.expanded
            ):
                self._toggle_branch(node)

        return handler

    def _move_focus(self, step: int, node: TreeNode, row: Div) -> None:
        """Move the focus ring to the next/previous row (depth-first
        visual order) and focus that row."""
        ordered = [self._row_by_key[n.resolved_key] for n in self._nodes]
        if row not in ordered:
            return
        idx = ordered.index(row)
        self._focus_row(ordered[(idx + step) % len(ordered)])
        self._unfocus_row(row)

    def _focus_row(self, row: Div) -> None:
        row.styles = row.styles.model_copy(update={"box_shadow": "0 0 0 2px var(--color-accent)"})

    def _unfocus_row(self, row: Div) -> None:
        row.styles = row.styles.model_copy(update={"box_shadow": None})

    def _make_branch_handler(self, node: TreeNode, row: Div):
        async def handler(event: DomEvent) -> None:
            self._toggle_branch(node)
            event.value = node.resolved_key
            event.source = "user"
            await self._dispatch("change", event)

        return handler

    def _toggle_branch(self, node: TreeNode) -> None:
        """Expand / collapse a branch by toggling its children column's
        display (and the chevron + aria-expanded)."""
        node.expanded = not node.expanded
        col = self._children_cols.get(node.resolved_key)
        if col is not None:
            col.styles = _CHILDREN_VISIBLE if node.expanded else _CHILDREN_HIDDEN
        row = self._row_by_key.get(node.resolved_key)
        if row is not None:
            chevron = row.container[0]
            if isinstance(chevron, Span):
                chevron.styles = _CHEVRON_OPEN if node.expanded else _CHEVRON
            row.args = {**row.args, "aria-expanded": "true" if node.expanded else "false"}

    def _make_leaf_handler(self, node: TreeNode, row: Div):
        async def handler(event: DomEvent) -> None:
            self.selected_key = node.resolved_key
            event.value = node.resolved_key
            event.source = "user"
            await self._dispatch("change", event)

        return handler

    def _make_shortcut_handler(self, key: str):
        async def handler() -> None:
            self.selected_key = key
            event = DomEvent(key=self._root.key, type="change", value=key)
            event.source = "user"
            await self._dispatch("change", event)

        return handler

    def _apply_leaf_active(self, node: TreeNode) -> None:
        row = self._row_by_key.get(node.resolved_key)
        if row is None:
            return
        active = node.resolved_key == self._selected_key
        row.styles = (_ROW_ACTIVE if active else _ROW_BASE).model_copy(
            update={"padding_left": calc(f"16px + {node._depth} * {_INDENT}")}
        )
        row.args = {**row.args, "aria-selected": "true" if active else "false"}

    def _sync_host(self) -> None:
        if self._selected_key is None:
            # With a fallback registered (slot 0), show it; else hide all.
            self._host.set_active(0 if self._fallback_slot is not None else -1)
            return
        try:
            index = self._leaf_keys.index(self._selected_key)
        except ValueError:
            self._host.set_active(0 if self._fallback_slot is not None else -1)
            return
        # Leaf slots start after the fallback slot (index 0) when present.
        self._host.set_active(index + (1 if self._fallback_slot is not None else 0))
