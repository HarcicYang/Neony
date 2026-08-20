"""Tests for the RichText inline editor component."""

import asyncio

from neony.application.elements import ImageSegment, RichText, TextSegment
from neony.dom import DomEvent


def _as_text(segment: TextSegment | ImageSegment) -> TextSegment:
    assert isinstance(segment, TextSegment)
    return segment


def _as_image(segment: TextSegment | ImageSegment) -> ImageSegment:
    assert isinstance(segment, ImageSegment)
    return segment


def test_build_is_managed_contenteditable():
    editor = RichText(segments=["你好", ImageSegment(src="x.png")])
    root = editor.build()
    assert root.args["contenteditable"] == "true"
    assert root.args["data-neony-rich-text"] == "true"
    assert root._managed_content is True
    assert root.bubble_events is True

    node = root.to_node()
    assert node.children[0].tag == "span"
    assert node.children[0].text == "你好"
    assert node.children[1].tag == "img"
    assert node.children[1].attrs["src"] == "x.png"
    assert node.children[1].styles["width"] == "40px"
    assert node.children[1].styles["height"] == "40px"
    assert node.children[1].styles["max-width"] == "min(320px, 100%)"
    assert node.children[1].styles["max-height"] == "240px"


def test_image_custom_size_is_capped():
    editor = RichText(segments=[ImageSegment(src="x.png", width=800, height="600px")])
    image = editor.build().to_node().children[0]
    assert image.styles["width"] == "800px"
    assert image.styles["height"] == "600px"
    assert image.styles["max-width"] == "min(320px, 100%)"
    assert image.styles["max-height"] == "240px"


def test_content_returns_ordered_segments():
    editor = RichText(segments=["你好", ImageSegment(src="x.png"), "世界"])
    content = editor.content()
    assert [type(seg).__name__ for seg in content] == ["TextSegment", "ImageSegment", "TextSegment"]
    assert _as_text(content[0]).text == "你好"
    assert _as_image(content[1]).src == "x.png"
    assert _as_text(content[2]).text == "世界"


def test_insert_text_merges_adjacent_text():
    editor = RichText(segments=["ab"])
    editor.insert_text("X", at_caret=True)
    content = editor.content()
    assert len(content) == 1
    assert _as_text(content[0]).text == "abX"
    assert editor.caret_position() == 3


def test_insert_image_splits_text_at_caret():
    editor = RichText(segments=["ab"])
    editor.set_caret(1)
    editor.insert_image("x.png", at_caret=True)
    content = editor.content()
    assert len(content) == 3
    assert _as_text(content[0]).text == "a"
    assert _as_image(content[1]).src == "x.png"
    assert _as_text(content[2]).text == "b"
    assert editor.caret_position() == 2


def test_set_content_replaces_model_and_dom_children():
    editor = RichText(segments=["old"])
    editor.set_content(["你", ImageSegment(src="y.png")])
    content = editor.content()
    assert _as_text(content[0]).text == "你"
    assert _as_image(content[1]).src == "y.png"
    assert len(editor._root.container) == 2


def test_on_event_updates_caret_and_selection():
    editor = RichText(segments=["abcd"])
    asyncio.run(
        editor._on_event(
            "click",
            DomEvent(key=editor._root.key, type="click", caret_position=2, selection_end=4),
        )
    )
    assert editor.caret_position() == 2
    assert editor.selection_range() == (2, 4)


def test_on_event_enter_dispatches_submit():
    editor = RichText(segments=[""])
    submitted = []
    editor.on_submit(lambda event: submitted.append(event))

    asyncio.run(
        editor._on_event(
            "keydown",
            DomEvent(key=editor._root.key, type="keydown", value="Enter"),
        )
    )
    assert len(submitted) == 1
    assert submitted[0].type == "keydown"
