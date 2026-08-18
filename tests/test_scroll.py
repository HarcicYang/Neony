"""Tests for ScrollArea and StickToBottom."""

import asyncio

from neony.application.elements import ScrollArea, StickToBottom
from neony.dom import Div, DOMElement


def test_scroll_area_has_scroll_mount_contract():
    area = ScrollArea()
    root = area.build()
    assert root.styles.overflow_y == "auto"
    assert root.styles.overflow_x == "hidden"
    assert root.styles.flex_grow == "1"
    assert root.styles.flex_basis == "0"
    assert root.styles.min_height == "0"


def test_scroll_area_mounts_component_children():
    area = ScrollArea(Div(container=["hello"]))
    root = area.build()
    assert len(root.container) == 1
    child = root.container[0]
    assert isinstance(child, DOMElement)
    assert child._tag == "div"
    assert "hello" in child.build()


def test_stick_to_bottom_carries_autostick_attribute():
    stick = StickToBottom()
    root = stick.build()
    assert root.args["data-neony-autostick"] == "true"
    assert root.styles.overflow_y == "auto"


def test_scroll_methods_are_awaitable_without_an_armed_window():
    area = ScrollArea()
    result = asyncio.run(area.scroll_to_bottom())
    assert result is area
    result = asyncio.run(area.scroll_to_top())
    assert result is area
    result = asyncio.run(area.scroll_to(120, behavior="smooth"))
    assert result is area


def test_stick_to_bottom_force_scroll_is_awaitable():
    stick = StickToBottom()
    assert asyncio.run(stick.scroll_to_bottom(force=True)) is stick
    assert asyncio.run(stick.scroll_to_bottom(force=False)) is stick
