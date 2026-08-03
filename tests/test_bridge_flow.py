"""Regression tests for the reactive event/render flow.

The critical invariant: ``rev`` increments only when a message is
actually sent. A re-render with no changes (e.g. a ``change`` event
after the state was already rendered) must not create a revision gap —
otherwise the JS engine's ``lastRev`` falls behind and the next real
patch triggers a full resync, wiping input state.
"""

import asyncio
from typing import Any, cast

from neony.application import Config, NeonApplication
from neony.application.elements import Input, Text, VStack
from neony.dom import DomEvent


class FakeWindow:
    """Minimal lumiview Window stand-in."""

    def __init__(self) -> None:
        self.mount_calls = 0
        self.patches: list[dict] = []

    async def eval_js(self, script: str) -> str:
        self.mount_calls += 1
        return '{"ok": true}'

    async def emit(self, event: str, payload: dict) -> None:
        assert event == "neony:patch"
        self.patches.append(payload)


def _mount(app: NeonApplication, fake: FakeWindow) -> None:
    """Wire the fake window into the bridge (bypasses type checks)."""
    app._neony._win = cast(Any, fake)


async def _fire(app: NeonApplication, key: str, event_type: str, value: Any = None) -> None:
    await app._neony._on_event(cast(Any, None), key=key, event_type=event_type, value=value)


def _build_app() -> tuple[NeonApplication, FakeWindow, dict]:
    app = NeonApplication(Config(auto_render=True))
    fake = FakeWindow()
    _mount(app, fake)

    inp = Input(placeholder="name")
    echo = Text("")
    inp.on_input(lambda e: setattr(echo, "text", f"hi {e.value}"))
    tree = VStack(inp, echo).build()

    app._tree = tree
    app._collect_handlers(tree)
    return app, fake, {"input": inp, "echo": echo}


class TestRevContinuity:
    """No revision gaps when re-renders produce no patches."""

    def test_unchanged_rerender_does_not_gap_rev(self):
        app, fake, els = _build_app()

        async def run() -> list[int]:
            await app.render()  # mount (rev 1)
            inp = els["input"]

            # user types → patch sent
            await _fire(app, inp._input.key, "input", "a")
            # change event on blur → diff finds nothing → NO patch, NO rev bump
            await _fire(app, inp._input.key, "change", "a")
            # user types again → next patch must be rev 2 (continuous), not 3
            await _fire(app, inp._input.key, "input", "ab")

            return [p["rev"] for p in fake.patches]

        revs = asyncio.run(run())
        assert revs == [2, 3], f"expected continuous revs, got {revs}"
        # and no spurious mount (resync) happened
        assert fake.mount_calls == 1

    def test_continuous_typing_stays_continuous(self):
        app, fake, els = _build_app()

        async def run() -> list[int]:
            await app.render()  # mount
            inp = els["input"]
            for ch in ("a", "ab", "abc"):
                await _fire(app, inp._input.key, "input", ch)
            return [p["rev"] for p in fake.patches]

        revs = asyncio.run(run())
        assert revs == [2, 3, 4]
        assert fake.mount_calls == 1

    def test_two_inputs_interleaved(self):
        """Typing in a second input after an empty re-render stays continuous."""
        app = NeonApplication(Config(auto_render=True))
        fake = FakeWindow()
        _mount(app, fake)

        a = Input(placeholder="a")
        b = Input(placeholder="b")
        echo_a = Text("")
        echo_b = Text("")
        a.on_input(lambda e: setattr(echo_a, "text", f"A{e.value}"))
        b.on_input(lambda e: setattr(echo_b, "text", f"B{e.value}"))
        tree = VStack(a, echo_a, b, echo_b).build()

        app._tree = tree
        app._collect_handlers(tree)

        async def run() -> list[int]:
            await app.render()  # mount rev 1
            # type in a
            await _fire(app, a._input.key, "input", "x")
            # focus leaves a → change with no diff
            await _fire(app, a._input.key, "change", "x")
            # type in b — must NOT resync
            await _fire(app, b._input.key, "input", "y")
            # echo state updated on the Python side
            assert echo_a.text == "Ax"
            assert echo_b.text == "By"
            return [p["rev"] for p in fake.patches]

        revs = asyncio.run(run())
        assert revs == [2, 3], f"expected continuous revs, got {revs}"
        assert fake.mount_calls == 1


class TestHandlerIsolation:
    """One failing handler must not break the event chain."""

    def test_failing_handler_does_not_block_others(self):
        app = NeonApplication(Config(auto_render=True))
        fake = FakeWindow()
        _mount(app, fake)

        calls: list[str] = []

        async def bad(_e: DomEvent) -> None:
            raise RuntimeError("boom")

        async def good(_e: DomEvent) -> None:
            calls.append("good")

        from neony.dom import Div

        div = Div()
        div._handlers["click"] = [bad, good]
        tree = div
        app._tree = tree
        app._collect_handlers(tree)

        asyncio.run(_fire(app, div.key, "click"))
        assert calls == ["good"]
