"""Popup click-away integration tests through the application bridge."""

from __future__ import annotations

import asyncio
from typing import Any, cast

from neony.application import Config, NeonApplication
from neony.application._helpers import _Entry
from neony.application.elements import CascadingDropdown, Dropdown, MenuBranch, VStack
from neony.dom.bridge import Neony


class _FakeWindow:
    def __init__(self) -> None:
        self.patches: list[dict[str, Any]] = []

    async def eval_js(self, script: str) -> str:
        return '{"ok": true}'

    async def emit(self, event: str, payload: dict[str, Any]) -> None:
        assert event == "neony:patch"
        self.patches.append(payload)


def _mount(
    component: Dropdown | CascadingDropdown, *, auto_render: bool = False
) -> tuple[NeonApplication, Neony, _FakeWindow]:
    app = NeonApplication(Config(auto_render=auto_render))
    tree = VStack(component).build()
    bridge = Neony(name="neony", mount_selector=app.config.mount_selector)
    fake = _FakeWindow()
    entry = _Entry(bridge, tree)
    entry.window = cast(Any, fake)
    app._entries.append(entry)
    app._registered.append(set())
    bridge._win = cast(Any, fake)
    app._collect_handlers(bridge, tree, 0, app._registered[0])
    return app, bridge, fake


def _mouse_down(bridge: Neony, key: str) -> None:
    asyncio.run(bridge._on_event(cast(Any, None), key=key, event_type="mousedown"))


def test_dropdown_backdrop_handler_is_registered_and_reopens() -> None:
    dropdown = Dropdown("Language", items=["English"])
    _app, bridge, _fake = _mount(dropdown)
    assert (dropdown._click_away.key, "mousedown") in bridge._handlers

    _mouse_down(bridge, dropdown._trigger.key)
    assert dropdown._open
    _mouse_down(bridge, dropdown._click_away.key)
    assert not dropdown._open
    _mouse_down(bridge, dropdown._trigger.key)
    assert dropdown._open


def test_cascade_trigger_child_bubbles_to_the_registered_owner() -> None:
    dropdown = CascadingDropdown("Theme", items=[MenuBranch("Palette", ["Dark"])])
    _app, bridge, _fake = _mount(dropdown)
    assert (dropdown._wrapper.key, "mousedown") in bridge._handlers
    assert (dropdown._trigger.key, "mousedown") not in bridge._handlers

    _mouse_down(bridge, dropdown._label_span.key)
    assert dropdown._open
    _mouse_down(bridge, dropdown._chevron.key)
    assert not dropdown._open


def test_cascade_branch_click_does_not_toggle_outer_popup() -> None:
    dropdown = CascadingDropdown("Theme", items=[MenuBranch("Palette", ["Dark"])])
    _app, bridge, _fake = _mount(dropdown)
    branch_key = next(iter(dropdown._branches))

    _mouse_down(bridge, dropdown._label_span.key)
    asyncio.run(bridge._on_event(cast(Any, None), key=branch_key, event_type="click"))
    assert dropdown._open
    assert dropdown._branches[branch_key].styles.display == "flex"


def test_cascade_close_emits_hidden_styles_after_open_branch() -> None:
    dropdown = CascadingDropdown("Theme", items=[MenuBranch("Palette", ["Dark"])])
    app, bridge, fake = _mount(dropdown, auto_render=True)
    branch_key = next(iter(dropdown._branches))

    async def run() -> None:
        await app.render()
        await bridge._on_event(cast(Any, None), key=dropdown._label_span.key, event_type="mousedown")
        await bridge._on_event(cast(Any, None), key=branch_key, event_type="click")
        await bridge._on_event(cast(Any, None), key=dropdown._label_span.key, event_type="mousedown")

    asyncio.run(run())
    popup_ops = [
        op
        for message in fake.patches
        for op in message["ops"]
        if op["op"] == "update_styles" and op["key"] == dropdown._popup.key
    ]
    assert popup_ops[-1]["set"]["display"] == "none"
    backdrop_ops = [
        op
        for message in fake.patches
        for op in message["ops"]
        if op["op"] == "update_styles" and op["key"] == dropdown._click_away.key
    ]
    assert backdrop_ops[-1]["set"]["display"] == "none"


def test_cascade_backdrop_handler_is_registered_and_reopens() -> None:
    dropdown = CascadingDropdown("Theme", items=[MenuBranch("Palette", ["Dark"])])
    _app, bridge, _fake = _mount(dropdown)
    assert (dropdown._wrapper.key, "mousedown") in bridge._handlers
    assert (dropdown._click_away.key, "mousedown") not in bridge._handlers

    _mouse_down(bridge, dropdown._label_span.key)
    assert dropdown._open
    _mouse_down(bridge, dropdown._click_away.key)
    assert not dropdown._open
    _mouse_down(bridge, dropdown._label_span.key)
    assert dropdown._open
