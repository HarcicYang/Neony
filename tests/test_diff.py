"""Table-driven tests for DiffEngine.diff()."""

from neony.dom import NodeDescriptor
from neony.dom.bridge import (
    CreatePatch,
    DiffEngine,
    MovePatch,
    RemovePatch,
    ReorderPatch,
    ReplacePatch,
    SetTextPatch,
    UpdateAttrsPatch,
    UpdateStylesPatch,
)


def nd(key, tag="div", text=None, children=None, styles=None, attrs=None):
    return NodeDescriptor(
        key=key,
        tag=tag,
        text=text,
        children=children or [],
        styles=styles or {},
        attrs=attrs or {},
    )


# ── helpers ──────────────────────────────────────────────────────


def patch_types(patches):
    """Return a set of patch type names from a patch list."""
    return {type(p).__name__ for p in patches}


def has_patch(patches, patch_type):
    """Check that at least one patch of *patch_type* is present."""
    return any(isinstance(p, patch_type) for p in patches)


# ── tests ────────────────────────────────────────────────────────


class TestFirstRender:
    def test_first_render_creates_root(self):
        tree = nd("root", "html")
        patches = DiffEngine.diff(None, tree)
        assert len(patches) == 1
        assert isinstance(patches[0], CreatePatch)
        assert patches[0].key == "root"


class TestNoChanges:
    def test_identical_trees_produce_no_patches(self):
        tree = nd("r", "div", children=[nd("a", "span", text="hi")])
        assert DiffEngine.diff(tree, tree) == []

    def test_empty_trees(self):
        tree = nd("r", "div")
        assert DiffEngine.diff(tree, tree) == []


class TestTextChanges:
    def test_text_modified(self):
        old = nd("t", "span", text="hello")
        new = nd("t", "span", text="world")
        patches = DiffEngine.diff(old, new)
        assert len(patches) == 1
        assert isinstance(patches[0], SetTextPatch)
        assert patches[0].text == "world"

    def test_text_set_from_none(self):
        old = nd("t", "span", text=None)
        new = nd("t", "span", text="hello")
        patches = DiffEngine.diff(old, new)
        assert has_patch(patches, SetTextPatch)

    def test_text_cleared(self):
        old = nd("t", "span", text="hello")
        new = nd("t", "span", text=None)
        patches = DiffEngine.diff(old, new)
        assert has_patch(patches, SetTextPatch)
        op = next(p for p in patches if isinstance(p, SetTextPatch))
        assert op.text == ""


class TestStyleChanges:
    def test_style_value_changed(self):
        old = nd("s", "div", styles={"color": "red"})
        new = nd("s", "div", styles={"color": "blue"})
        patches = DiffEngine.diff(old, new)
        assert has_patch(patches, UpdateStylesPatch)
        op = next(p for p in patches if isinstance(p, UpdateStylesPatch))
        assert op.set == {"color": "blue"}
        assert op.remove == []

    def test_style_added(self):
        old = nd("s", "div", styles={})
        new = nd("s", "div", styles={"color": "red"})
        patches = DiffEngine.diff(old, new)
        assert has_patch(patches, UpdateStylesPatch)

    def test_style_removed(self):
        old = nd("s", "div", styles={"color": "red", "font-size": "16px"})
        new = nd("s", "div", styles={"color": "red"})
        patches = DiffEngine.diff(old, new)
        assert has_patch(patches, UpdateStylesPatch)
        op = next(p for p in patches if isinstance(p, UpdateStylesPatch))
        assert "font-size" in op.remove
        assert op.set == {}

    def test_style_add_and_remove(self):
        old = nd("s", "div", styles={"color": "red"})
        new = nd("s", "div", styles={"font-size": "16px"})
        patches = DiffEngine.diff(old, new)
        op = next(p for p in patches if isinstance(p, UpdateStylesPatch))
        assert "color" in op.remove
        assert op.set == {"font-size": "16px"}

    def test_styles_unchanged(self):
        old = nd("s", "div", styles={"color": "red"})
        new = nd("s", "div", styles={"color": "red"})
        patches = DiffEngine.diff(old, new)
        assert not has_patch(patches, UpdateStylesPatch)


class TestAttrChanges:
    def test_attr_changed(self):
        old = nd("a", "input", attrs={"type": "text"})
        new = nd("a", "input", attrs={"type": "password"})
        patches = DiffEngine.diff(old, new)
        assert has_patch(patches, UpdateAttrsPatch)

    def test_attr_added(self):
        old = nd("a", "div", attrs={})
        new = nd("a", "div", attrs={"class": "new"})
        patches = DiffEngine.diff(old, new)
        op = next(p for p in patches if isinstance(p, UpdateAttrsPatch))
        assert op.set == {"class": "new"}

    def test_attr_removed(self):
        old = nd("a", "div", attrs={"class": "old"})
        new = nd("a", "div", attrs={})
        patches = DiffEngine.diff(old, new)
        op = next(p for p in patches if isinstance(p, UpdateAttrsPatch))
        assert "class" in op.remove


class TestTagChange:
    def test_tag_change_produces_replace(self):
        old = nd("r", "div")
        new = nd("r", "span")
        patches = DiffEngine.diff(old, new)
        assert len(patches) == 1
        assert isinstance(patches[0], ReplacePatch)
        assert patches[0].node.tag == "span"


class TestChildChanges:
    def test_child_appended(self):
        old = nd("r", "div", children=[nd("a", "span")])
        new = nd("r", "div", children=[nd("a", "span"), nd("b", "span")])
        patches = DiffEngine.diff(old, new)
        creates = [p for p in patches if isinstance(p, CreatePatch)]
        assert len(creates) == 1
        assert creates[0].key == "b"

    def test_child_removed(self):
        old = nd("r", "div", children=[nd("a", "span"), nd("b", "span")])
        new = nd("r", "div", children=[nd("a", "span")])
        patches = DiffEngine.diff(old, new)
        removes = [p for p in patches if isinstance(p, RemovePatch)]
        assert len(removes) == 1
        assert removes[0].key == "b"

    def test_child_replaced_with_different_key(self):
        old = nd("r", "div", children=[nd("a", "span")])
        new = nd("r", "div", children=[nd("b", "span")])
        patches = DiffEngine.diff(old, new)
        assert has_patch(patches, RemovePatch)
        assert has_patch(patches, CreatePatch)

    def test_nested_child_changed(self):
        old = nd("r", "div", children=[nd("a", "span", text="old")])
        new = nd("r", "div", children=[nd("a", "span", text="new")])
        patches = DiffEngine.diff(old, new)
        assert has_patch(patches, SetTextPatch)


class TestReorder:
    def test_reorder_patch_emitted(self):
        old = nd("r", "div", children=[nd("a", "span"), nd("b", "span")])
        new = nd("r", "div", children=[nd("b", "span"), nd("a", "span")])
        patches = DiffEngine.diff(old, new)
        assert has_patch(patches, ReorderPatch)
        op = next(p for p in patches if isinstance(p, ReorderPatch))
        assert op.ordered_keys == ["b", "a"]

    def test_reorder_not_emitted_when_adding(self):
        old = nd("r", "div", children=[nd("a", "span")])
        new = nd("r", "div", children=[nd("a", "span"), nd("b", "span")])
        patches = DiffEngine.diff(old, new)
        assert not has_patch(patches, ReorderPatch)


class TestCombinedChanges:
    def test_multiple_changes(self):
        old = nd(
            "r",
            "div",
            styles={"color": "red"},
            children=[nd("a", "span", text="hi")],
        )
        new = nd(
            "r",
            "div",
            styles={"color": "blue"},
            children=[nd("a", "span", text="bye")],
        )
        patches = DiffEngine.diff(old, new)
        assert has_patch(patches, UpdateStylesPatch)
        assert has_patch(patches, SetTextPatch)


class TestReorderWithAddRemove:
    """Reorder + add/remove combinations produce correct patches.

    The diff algorithm must handle scenarios where elements are added,
    removed, and reordered simultaneously. The strategy:
    1. Remove elements not in new_children
    2. Create new elements (temporarily appended, index=None)
    3. ReorderPatch fixes the final order for all elements
    """

    def test_reorder_with_add(self):
        """Adding an element and reordering triggers ReorderPatch."""
        old = nd("r", "div", children=[nd("a", "span"), nd("b", "span"), nd("c", "span")])
        new = nd("r", "div", children=[nd("b", "span"), nd("c", "span"), nd("a", "span"), nd("d", "span")])
        patches = DiffEngine.diff(old, new)

        assert has_patch(patches, CreatePatch)
        create = next(p for p in patches if isinstance(p, CreatePatch))
        assert create.key == "d"
        assert create.index is None  # Appended to end, Reorder fixes position

        assert has_patch(patches, ReorderPatch)
        reorder = next(p for p in patches if isinstance(p, ReorderPatch))
        assert reorder.ordered_keys == ["b", "c", "a", "d"]

    def test_reorder_with_remove(self):
        """Removing an element and reordering triggers ReorderPatch."""
        old = nd("r", "div", children=[nd("a", "span"), nd("b", "span"), nd("c", "span"), nd("d", "span")])
        new = nd("r", "div", children=[nd("b", "span"), nd("d", "span"), nd("a", "span")])
        patches = DiffEngine.diff(old, new)

        assert has_patch(patches, RemovePatch)
        remove = next(p for p in patches if isinstance(p, RemovePatch))
        assert remove.key == "c"

        assert has_patch(patches, ReorderPatch)
        reorder = next(p for p in patches if isinstance(p, ReorderPatch))
        assert reorder.ordered_keys == ["b", "d", "a"]

    def test_reorder_with_add_and_remove(self):
        """Adding, removing, and reordering simultaneously."""
        old = nd("r", "div", children=[nd("a", "span"), nd("b", "span"), nd("c", "span"), nd("d", "span")])
        new = nd("r", "div", children=[nd("b", "span"), nd("d", "span"), nd("e", "span"), nd("a", "span")])
        patches = DiffEngine.diff(old, new)

        # Remove c
        removes = [p for p in patches if isinstance(p, RemovePatch)]
        assert len(removes) == 1
        assert removes[0].key == "c"

        # Create e
        creates = [p for p in patches if isinstance(p, CreatePatch)]
        assert len(creates) == 1
        assert creates[0].key == "e"
        assert creates[0].index is None

        # Reorder all remaining
        assert has_patch(patches, ReorderPatch)
        reorder = next(p for p in patches if isinstance(p, ReorderPatch))
        assert reorder.ordered_keys == ["b", "d", "e", "a"]

    def test_complex_reorder_scenario(self):
        """Complex scenario: multiple adds, removes, and reorders."""
        old = nd(
            "r",
            "div",
            children=[nd("a", "span"), nd("b", "span"), nd("c", "span"), nd("d", "span"), nd("e", "span")],
        )
        new = nd(
            "r",
            "div",
            children=[nd("e", "span"), nd("c", "span"), nd("a", "span"), nd("f", "span"), nd("g", "span")],
        )
        patches = DiffEngine.diff(old, new)

        # Remove b and d
        removes = [p for p in patches if isinstance(p, RemovePatch)]
        remove_keys = {p.key for p in removes}
        assert remove_keys == {"b", "d"}

        # Create f and g
        creates = [p for p in patches if isinstance(p, CreatePatch)]
        create_keys = {p.key for p in creates}
        assert create_keys == {"f", "g"}
        for c in creates:
            assert c.index is None

        # Reorder all remaining
        assert has_patch(patches, ReorderPatch)
        reorder = next(p for p in patches if isinstance(p, ReorderPatch))
        assert reorder.ordered_keys == ["e", "c", "a", "f", "g"]

    def test_no_reorder_when_only_adding(self):
        """Adding without reordering does not emit ReorderPatch."""
        old = nd("r", "div", children=[nd("a", "span")])
        new = nd("r", "div", children=[nd("a", "span"), nd("b", "span")])
        patches = DiffEngine.diff(old, new)

        assert has_patch(patches, CreatePatch)
        assert not has_patch(patches, ReorderPatch)

    def test_no_reorder_when_only_removing(self):
        """Removing without reordering does not emit ReorderPatch."""
        old = nd("r", "div", children=[nd("a", "span"), nd("b", "span")])
        new = nd("r", "div", children=[nd("a", "span")])
        patches = DiffEngine.diff(old, new)

        assert has_patch(patches, RemovePatch)
        assert not has_patch(patches, ReorderPatch)


class TestCrossBoard:
    """Two boards exchanging a card — the diff must not lose the moved
    element or drop it at the wrong index."""

    def old_tree(self):
        return nd(
            "page",
            "div",
            children=[
                nd("grid", "div", children=[nd("g1", "span"), nd("g2", "span"), nd("g3", "span")]),
                nd("tray", "div", children=[nd("t1", "span")]),
            ],
        )

    def test_cross_parent_move_emits_move_patch(self):
        """Moving t1 from the tray into the grid is a CROSS-PARENT move:
        the same element must be re-parented (MovePatch), never
        remove+create — a create would build a fresh node that the
        trailing remove then deletes (blank slot), or double-render."""
        old = self.old_tree()
        new = nd(
            "page",
            "div",
            children=[
                nd("grid", "div", children=[nd("g1", "span"), nd("g2", "span"), nd("t1", "span"), nd("g3", "span")]),
                nd("tray", "div", children=[]),
            ],
        )
        patches = DiffEngine.diff(old, new)
        move = next(p for p in patches if isinstance(p, MovePatch))
        assert move.key == "t1"
        assert move.to_parent == "grid"
        assert move.to_index == 2  # g1, g2, [t1], g3
        assert not has_patch(patches, RemovePatch)
        assert not has_patch(patches, CreatePatch)
        assert not has_patch(patches, ReorderPatch)

    def test_cross_parent_move_same_parent_is_reorder(self):
        """A same-parent key stays a plain reorder — no MovePatch."""
        old = self.old_tree()
        new = nd(
            "page",
            "div",
            children=[
                nd("grid", "div", children=[nd("g2", "span"), nd("g1", "span"), nd("g3", "span")]),
                nd("tray", "div", children=[nd("t1", "span")]),
            ],
        )
        patches = DiffEngine.diff(old, new)
        assert not has_patch(patches, MovePatch)
        assert has_patch(patches, ReorderPatch)

    def test_same_key_in_two_boards_does_not_move(self):
        """A key that exists in BOTH boards (duplicate keys — not a move)
        must not emit a MovePatch for either."""
        old = nd(
            "page",
            "div",
            children=[
                nd("grid", "div", children=[nd("a", "span"), nd("x", "span")]),
                nd("tray", "div", children=[nd("x", "span")]),
            ],
        )
        new = nd(
            "page",
            "div",
            children=[
                nd("grid", "div", children=[nd("a", "span"), nd("x", "span")]),
                nd("tray", "div", children=[nd("x", "span")]),
            ],
        )
        patches = DiffEngine.diff(old, new)
        assert not has_patch(patches, MovePatch)
