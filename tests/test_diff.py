"""Table-driven tests for DiffEngine.diff()."""

from neony.dom import NodeDescriptor
from neony.dom.bridge import (
    CreatePatch,
    DiffEngine,
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
