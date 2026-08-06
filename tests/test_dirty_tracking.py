"""Tests for dirty-subtree tracking.

The render path reuses cached NodeDescriptor snapshots for elements that
didn't change since the last render.  A mutation must mark the element —
and, via parent pointers, every ancestor — dirty, otherwise a parent's
cached snapshot (holding the stale child) would be reused.
"""

from neony.dom import Color, Div, NodeDescriptor, Span, Styles


def _cache() -> dict[str, NodeDescriptor]:
    return {}


def build_tree():
    """root > a(span) > b(span) + c(span)."""
    b = Span(key="b", container=["B"])
    c = Span(key="c", container=["C"])
    a = Span(key="a", container=[b, c])
    root = Div(key="root", container=[a])
    return root, a, b, c


class TestDirtyMarking:
    def _clean(self, root, a, b, c):
        """Clear the build-time dirty flags (constructor field writes
        mark elements dirty; a full serialization clears them)."""
        root.to_node(_cache())
        return root, a, b, c

    def test_field_assignment_marks_dirty(self):
        root, a, _b, _c = self._clean(*build_tree())
        assert not root._dirty
        a.container = ["changed"]
        assert a._dirty
        assert root._dirty  # propagated

    def test_mutation_propagates_to_ancestors(self):
        root, a, b, _c = self._clean(*build_tree())
        b.container = ["B2"]
        assert b._dirty
        assert a._dirty  # parent chain
        assert root._dirty  # up to the root

    def test_sibling_mutation_does_not_mark_other_siblings(self):
        _root, _a, b, c = self._clean(*build_tree())
        b.container = ["B2"]
        assert not c._dirty

    def test_container_append_marks_owner_dirty(self):
        root, a, _b, _c = self._clean(*build_tree())
        new = Span(container=["new"])
        a.container.append(new)
        assert a._dirty
        assert root._dirty

    def test_container_remove_marks_owner_dirty(self):
        _root, a, b, _c = self._clean(*build_tree())
        a.container.remove(b)
        assert a._dirty
        assert b._parent is None  # parent pointer dropped

    def test_in_place_styles_field_mutation_marks_dirty(self):
        """`el.styles.foo = X` (a field on the existing Styles model)
        must mark the element dirty — the gallery's set_dot() pattern."""
        root, a, _b, _c = self._clean(*build_tree())
        a.styles.background_color = Color(var="--color-accent")
        assert a._dirty
        assert root._dirty  # propagated to ancestors

    def test_styles_field_mutation_after_full_reassignment(self):
        """model_copy reassignment re-hooks the new Styles instance."""
        root, a, _b, _c = self._clean(*build_tree())
        a.styles = a.styles.model_copy(update={"padding": "8px"})
        assert a._dirty  # the reassignment itself marks dirty
        # A render clears the flags; the *new* Styles instance must
        # still report mutations against the same element.
        root.to_node(_cache())
        assert not a._dirty
        a.styles.padding = "16px"
        assert a._dirty
        assert root._dirty

    def test_parent_pointers_maintained_on_append(self):
        root, a, b, _c = build_tree()
        assert b._parent is a
        assert a._parent is root
        assert root._parent is None

    def test_mark_dirty_explicit(self):
        root, a, _b, c = self._clean(*build_tree())
        c.mark_dirty()
        assert c._dirty
        assert a._dirty
        assert root._dirty


class TestSnapshotReuse:
    def test_clean_element_reuses_cached_snapshot(self):
        root, _a, _b, _c = build_tree()
        cache = _cache()
        node1 = root.to_node(snapshot_cache=cache)
        assert len(cache) == 4

        # Nothing changed — serializing again returns the SAME objects.
        node2 = root.to_node(snapshot_cache=cache)
        assert node2 is node1
        assert node2.children[0] is node1.children[0]

    def test_dirty_element_reserializes_clean_children_from_cache(self):
        root, _a, b, _c = build_tree()
        cache = _cache()
        node1 = root.to_node(snapshot_cache=cache)

        b.container = ["B2"]  # b dirty → a and root dirty; c clean
        node2 = root.to_node(snapshot_cache=cache)

        a2 = node2.children[0]
        # a re-serialized (dirty), c reused verbatim from the cache
        assert a2 is not node1.children[0]
        assert a2.children[1] is node1.children[0].children[1]  # c: cached
        # b re-serialized with the new text
        assert a2.children[0].text == "B2"
        assert node2 is not node1

    def test_dirty_cleared_after_serialization(self):
        root, a, b, _c = build_tree()
        cache = _cache()
        root.to_node(snapshot_cache=cache)
        assert not root._dirty and not a._dirty and not b._dirty

        b.container = ["B2"]
        root.to_node(snapshot_cache=cache)
        assert not b._dirty and not a._dirty and not root._dirty

    def test_clean_subtree_not_walked(self):
        """A clean element's serialization must not recurse into its
        children — verified by removing the children first: the cached
        snapshot still carries them."""
        root, a, _b, _c = build_tree()
        cache = _cache()
        root.to_node(snapshot_cache=cache)

        # rip b out of the live tree WITHOUT marking a dirty — a "cheat"
        # that must not leak into the reused snapshot
        a.container.clear()
        a._dirty = False
        node2 = root.to_node(snapshot_cache=cache)
        # a is clean → reused from cache, children intact
        assert len(node2.children[0].children) == 2


class TestDiffIntegration:
    def test_unchanged_reserialize_produces_no_patches(self):
        from neony.dom.bridge import DiffEngine

        root, *_ = build_tree()
        cache = _cache()
        n1 = root.to_node(snapshot_cache=cache)
        n2 = root.to_node(snapshot_cache=cache)
        assert DiffEngine.diff(n1, n2) == []

    def test_partial_change_produces_minimal_patches(self):
        from neony.dom.bridge import DiffEngine, SetTextPatch

        root, _a, b, _c = build_tree()
        cache = _cache()
        n1 = root.to_node(snapshot_cache=cache)
        b.container = ["B2"]
        n2 = root.to_node(snapshot_cache=cache)
        patches = DiffEngine.diff(n1, n2)
        # exactly one real change: b's text
        text_patches = [p for p in patches if isinstance(p, SetTextPatch)]
        assert len(text_patches) == 1
        assert text_patches[0].key == "b"
        assert text_patches[0].text == "B2"

    def test_style_change_on_component_propagates(self):
        from neony.application.elements import Button

        btn = Button("click")
        cache = _cache()
        n1 = btn._root.to_node(snapshot_cache=cache)
        btn.reset_styles(Styles(opacity=0.5))
        assert btn._root._dirty
        n2 = btn._root.to_node(snapshot_cache=cache)
        assert n2.styles.get("opacity") == "0.5"
        assert n1.styles.get("opacity") is None
