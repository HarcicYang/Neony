"""Dirty-driven render scheduling for mounted DOM trees."""

from __future__ import annotations

import asyncio
from typing import Any, cast

from neony.application import Config, NeonApplication
from neony.application._helpers import _Entry
from neony.dom import Div, Styles
from neony.dom.bridge import Neony


class _FakeWindow:
    def __init__(self) -> None:
        self.patches: list[dict[str, Any]] = []

    async def eval_js(self, script: str) -> str:
        return '{"ok": true}'

    async def emit(self, event: str, payload: dict[str, Any]) -> None:
        assert event == "neony:patch"
        self.patches.append(payload)


def _mounted(*, auto_render: bool = True) -> tuple[NeonApplication, Div, _FakeWindow]:
    app = NeonApplication(Config(auto_render=auto_render))
    tree = Div(key="root", container=[Div(key="child")])
    fake = _FakeWindow()
    bridge = Neony(name="neony", mount_selector=app.config.mount_selector)
    entry = _Entry(bridge, tree)
    entry.window = cast(Any, fake)
    app._entries.append(entry)
    app._registered.append(set())
    bridge._win = cast(Any, fake)
    app._collect_handlers(bridge, tree, 0, app._registered[0])
    app._arm_render_request(tree, 0)
    return app, tree, fake


def test_async_mutation_schedules_render_without_dom_event() -> None:
    app, tree, fake = _mounted()
    child = cast(Div, tree.container[0])

    async def run() -> None:
        await app.render()
        child.styles = Styles(display="none")
        await asyncio.sleep(0)
        await asyncio.sleep(0)

    asyncio.run(run())
    assert fake.patches[-1]["ops"] == [
        {"op": "update_styles", "key": "child", "set": {"display": "none"}, "remove": []}
    ]


def test_same_turn_mutations_coalesce_to_one_render() -> None:
    app, tree, fake = _mounted()
    child = cast(Div, tree.container[0])

    async def run() -> None:
        await app.render()
        child.styles = Styles(display="flex")
        child.args = {"aria-hidden": "false"}
        child.styles = Styles(display="none")
        assert len(app._scheduled_renders) == 1
        await asyncio.sleep(0)
        await asyncio.sleep(0)

    asyncio.run(run())
    assert len(fake.patches) == 1
    ops = fake.patches[0]["ops"]
    assert [op["op"] for op in ops] == ["update_styles", "update_attrs"]
    assert ops[0]["set"]["display"] == "none"


def test_mutation_during_render_queues_followup_commit() -> None:
    app, tree, fake = _mounted()
    child = cast(Div, tree.container[0])
    mutated = False
    original_emit = fake.emit

    async def emit(event: str, payload: dict[str, Any]) -> None:
        nonlocal mutated
        await original_emit(event, payload)
        if not mutated:
            mutated = True
            child.args = {"data-after": "render"}

    fake.emit = emit

    async def run() -> None:
        await app.render()
        child.styles = Styles(display="none")
        for _ in range(5):
            await asyncio.sleep(0)

    asyncio.run(run())
    assert [op["op"] for message in fake.patches for op in message["ops"]] == [
        "update_styles",
        "update_attrs",
    ]


def test_auto_render_false_does_not_schedule() -> None:
    app, tree, fake = _mounted(auto_render=False)
    child = cast(Div, tree.container[0])

    async def run() -> None:
        await app.render()
        child.styles = Styles(display="none")
        await asyncio.sleep(0)
        assert not app._scheduled_renders

    asyncio.run(run())
    assert fake.patches == []
