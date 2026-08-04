"""Tests for cross-window reactivity.

A shared signal bound to elements in several windows' trees: one write
updates every window that has a binding — each through its own tree root
render request — while windows without a binding stay quiet.
"""

import asyncio
from typing import Any, cast

from neony.application import Config, NeonApplication
from neony.application.app import _Entry
from neony.application.elements import Text
from neony.dom import SharedSignal
from neony.dom.bridge import Neony


class FakeWindow:
    """Lumiview Window stand-in that records patch messages."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.patches: list[dict] = []

    async def eval_js(self, script: str) -> str:
        return '{"ok": true}'

    async def emit(self, event: str, payload: dict) -> None:
        assert event == "neony:patch"
        self.patches.append(payload)


def add_window(app: NeonApplication, tree, fake: FakeWindow) -> Neony:
    """Register one window's bridge, handlers, and render request."""
    neony = Neony(name="neony", mount_selector=app.config.mount_selector)
    idx = len(app._entries)
    entry = _Entry(neony, tree)
    entry.window = cast(Any, fake)
    app._entries.append(entry)
    neony._win = cast(Any, fake)
    app._collect_handlers(neony, tree, idx)
    app._arm_render_request(tree, idx)
    return neony


class TestSharedSignal:
    def test_shared_signal_is_a_signal(self):
        s = SharedSignal(0)
        s.set(1)
        assert s() == 1


class TestCrossWindowUpdates:
    def test_write_updates_every_bound_window(self):
        app = NeonApplication(Config(auto_render=True))
        win_a = FakeWindow("a")
        win_b = FakeWindow("b")

        count = SharedSignal(0)
        label_a = Text("0")
        label_a.bind_text(count)
        label_b = Text("0")
        label_b.bind_text(count)

        add_window(app, label_a._root, win_a)
        add_window(app, label_b._root, win_b)

        async def run():
            await app.render()  # mounts both windows (rev 1 each)
            count.set(5)  # one write → both windows schedule renders
            await asyncio.sleep(0.02)
            return (
                [p["rev"] for p in win_a.patches],
                [p["rev"] for p in win_b.patches],
            )

        revs_a, revs_b = asyncio.run(run())
        # mounts go through eval_js (not recorded); one diff patch each
        assert revs_a == [2], f"window A revs: {revs_a}"
        assert revs_b == [2], f"window B revs: {revs_b}"
        # both patches carry the updated text
        text_a = [op for op in win_a.patches[-1]["ops"] if op["op"] == "set_text"]
        text_b = [op for op in win_b.patches[-1]["ops"] if op["op"] == "set_text"]
        assert text_a[0]["text"] == "5"
        assert text_b[0]["text"] == "5"

    def test_unbound_window_stays_quiet(self):
        app = NeonApplication(Config(auto_render=True))
        win_a = FakeWindow("a")
        win_b = FakeWindow("b")

        count = SharedSignal(0)
        label_a = Text("0")
        label_a.bind_text(count)
        plain_b = Text("0")  # window B has NO binding on count

        add_window(app, label_a._root, win_a)
        add_window(app, plain_b._root, win_b)

        async def run():
            await app.render()
            count.set(1)
            await asyncio.sleep(0.02)
            return len(win_b.patches)

        n = asyncio.run(run())
        assert n == 0, f"window B has no binding — expected no patches, got {n}"

    def test_other_signals_do_not_leak_across_windows(self):
        app = NeonApplication(Config(auto_render=True))
        win_a = FakeWindow("a")
        win_b = FakeWindow("b")

        local_a = SharedSignal("a-value")
        local_b = SharedSignal("b-value")
        label_a = Text("")
        label_a.bind_text(local_a)
        label_b = Text("")
        label_b.bind_text(local_b)

        add_window(app, label_a._root, win_a)
        add_window(app, label_b._root, win_b)

        async def run():
            await app.render()
            local_b.set("b-changed")  # only window B's binding fires
            await asyncio.sleep(0.02)
            return len(win_a.patches)

        n = asyncio.run(run())
        assert n == 0, f"window A must not react to B's signal, got {n} patches"
