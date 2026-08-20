"""Dialog exit-animation integration tests through the application bridge."""

from __future__ import annotations

import asyncio
from typing import Any, cast

from neony.application import Config, NeonApplication
from neony.application._helpers import _Entry
from neony.application.elements import Dialog, VStack
from neony.dom.bridge import Neony


class _FakeWindow:
    def __init__(self) -> None:
        self.patches: list[dict[str, Any]] = []

    async def eval_js(self, script: str) -> str:
        return '{"ok": true}'

    async def emit(self, event: str, payload: dict[str, Any]) -> None:
        assert event == "neony:patch"
        self.patches.append(payload)


def test_animationend_emits_final_display_none_patch() -> None:
    dialog = Dialog(open=True)
    app = NeonApplication(Config(auto_render=True))
    tree = VStack(dialog).build()
    bridge = Neony(name="neony", mount_selector=app.config.mount_selector)
    fake = _FakeWindow()
    entry = _Entry(bridge, tree)
    entry.window = cast(Any, fake)
    app._entries.append(entry)
    app._registered.append(set())
    bridge._win = cast(Any, fake)
    app._collect_handlers(bridge, tree, 0, app._registered[0])

    async def run() -> None:
        await app.render()
        await bridge._on_event(cast(Any, None), key=dialog._scrim.key, event_type="click")
        assert dialog._root.styles.display == "flex"
        await bridge._on_event(
            cast(Any, None),
            key=dialog._panel.key,
            event_type="animationend",
            animation_name="fade-slide",
            elapsed_time=0.2,
        )

    asyncio.run(run())
    root_ops = [
        op
        for message in fake.patches
        for op in message["ops"]
        if op["op"] == "update_styles" and op["key"] == dialog._root.key
    ]
    assert root_ops[-1]["set"]["display"] == "none"
