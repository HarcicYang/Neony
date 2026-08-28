"""GridView — responsive grid container with typed column tracks."""

import pytest
from pydantic import ValidationError

from neony.application.elements import Card, GridView, Text
from neony.dom import Columns, Div, DOMElement, Styles

# ---- Columns serialization -------------------------------------------------


def test_columns_fixed_repeats_1fr():
    assert str(Columns.fixed(3)) == "repeat(3, 1fr)"


def test_columns_responsive_auto_fill():
    assert str(Columns.responsive(120)) == "repeat(auto-fill, minmax(120px, 1fr))"


def test_columns_responsive_fit_uses_auto_fit():
    assert str(Columns.responsive("116px", fit=True)) == "repeat(auto-fit, minmax(116px, 1fr))"


def test_columns_bare_number_becomes_px():
    assert str(Columns.responsive(90.5)) == "repeat(auto-fill, minmax(90.5px, 1fr))"


def test_columns_tracks_are_space_joined():
    assert str(Columns(tracks=("80px", "1fr", "2fr"))) == "80px 1fr 2fr"


def test_columns_rejects_multiple_definitions():
    with pytest.raises(ValidationError):
        Columns(repeat=2, min_width="120px")
    with pytest.raises(ValidationError):
        Columns(min_width="120px", tracks=("1fr",))


def test_columns_string_path_through_union_survives():
    """A raw string on ``Styles.grid_template_columns`` must stay itself —
    pydantic serialises union members duck-typed, so a field name that
    collides with a ``str`` method would silently mis-serialise."""
    styles = Styles(grid_template_columns="80px 1fr")
    assert styles.model_dump(exclude_none=True)["grid_template_columns"] == "80px 1fr"


def test_columns_rejects_empty_definition():
    with pytest.raises(ValidationError):
        Columns()


def test_columns_fit_requires_min_width():
    with pytest.raises(ValidationError):
        Columns(fit=True)


def test_columns_renders_kebab_case_through_node():
    node = Div(styles=Styles(grid_template_columns=Columns.fixed(2))).to_node()
    assert node.styles["grid-template-columns"] == "repeat(2, 1fr)"


# ---- GridView build --------------------------------------------------------


def test_grid_view_default_columns_and_gap():
    root = GridView().build()
    assert root.styles.display == "grid"
    assert str(root.styles.grid_template_columns) == "repeat(auto-fill, minmax(120px, 1fr))"
    assert root.styles.gap == "8px"
    assert root.container == []


def test_grid_view_wraps_children_in_items():
    card = Card(Text("a"))
    root = GridView(card, Div(), "plain").build()
    assert len(root.container) == 3
    for item in root.container:
        # Each child sits in its own grid item wrapper (str children too).
        assert isinstance(item, DOMElement)
        assert item.styles.min_width == "0"
        assert item.styles.word_break == "break-word"
    # The Component child was mounted exactly once (its build is consumed).
    assert card._built


def test_grid_view_uniform_row_stretch():
    root = GridView(Card(Text("a")), Card(Text("b"))).build()
    for item in root.container:
        # Nested one-cell grid: the child stretches to the row height.
        assert isinstance(item, DOMElement)
        assert item.styles.display == "grid"


def test_grid_view_natural_heights_top_align():
    root = GridView(Card(Text("a")), uniform=False).build()
    assert root.styles.align_items == "start"
    # No nested grid — items stay content-sized.
    item = root.container[0]
    assert isinstance(item, DOMElement)
    assert item.styles.display is None


def test_grid_view_tracks_component_children():
    card = Card(Text("a"))
    grid = GridView(card)
    assert any(c is card for c in grid.iter_components())


def test_grid_view_accepts_custom_columns():
    root = GridView(columns=Columns(tracks=("1fr", "2fr"))).build()
    assert str(root.styles.grid_template_columns) == "1fr 2fr"
