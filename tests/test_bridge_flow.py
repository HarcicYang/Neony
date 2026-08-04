"""Regression tests for the reactive event/render flow.

The critical invariant: ``rev`` increments only when a message is
actually sent — an empty re-render must not create a revision gap, or
the JS engine's ``lastRev`` falls behind and the next real patch
triggers a full resync, wiping input state.
"""

import asyncio
from types import SimpleNamespace
from typing import Any, cast

import pytest

from neony.application import Config, NeonApplication
from neony.application.app import _Entry
from neony.application.elements import Button, Input, Text, VStack
from neony.dom import Div, DomEvent
from neony.dom.bridge import Neony


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


def _setup_entry(app: NeonApplication, tree, fake: FakeWindow) -> Neony:
    """Simulate run()'s per-window setup without starting LumiView."""
    neony = Neony(name="neony", mount_selector=app.config.mount_selector)
    entry = _Entry(neony, tree)
    entry.window = cast(Any, fake)  # render() gates on entry.window
    app._entries.append(entry)
    neony._win = cast(Any, fake)  # wire the fake window into the bridge
    app._collect_handlers(neony, tree, 0)
    return neony


async def _fire(app: NeonApplication, key: str, event_type: str, value: Any = None) -> None:
    await app._entries[0].neony._on_event(cast(Any, None), key=key, event_type=event_type, value=value)


def _build_app() -> tuple[NeonApplication, FakeWindow, dict]:
    app = NeonApplication(Config(auto_render=True))
    fake = FakeWindow()

    inp = Input(placeholder="name")
    echo = Text("")
    inp.on_input(lambda e: setattr(echo, "text", f"hi {e.value}"))
    tree = VStack(inp, echo).build()

    _setup_entry(app, tree, fake)
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

        a = Input(placeholder="a")
        b = Input(placeholder="b")
        echo_a = Text("")
        echo_b = Text("")
        a.on_input(lambda e: setattr(echo_a, "text", f"A{e.value}"))
        b.on_input(lambda e: setattr(echo_b, "text", f"B{e.value}"))
        tree = VStack(a, echo_a, b, echo_b).build()

        _setup_entry(app, tree, fake)

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


class TestDeferredRender:
    """Hover / focus / blur events coalesce into one deferred render.

    Immediate-path events (input, click) still render synchronously —
    those tests live in TestRevContinuity above.
    """

    def test_hover_defers_render(self):
        app, fake, els = _build_app()
        inp = els["input"]

        async def run():
            await app.render()  # mount rev 1
            # focus is a deferred event — no patch arrives immediately
            await _fire(app, inp._input.key, "focus")
            assert fake.patches == [], "deferred render must not fire synchronously"
            await asyncio.sleep(0.05)  # > debounce window (16ms)
            return [p["rev"] for p in fake.patches]

        revs = asyncio.run(run())
        assert revs == [2]

    def test_rapid_hover_burst_coalesces(self):
        """A burst of deferred events within the debounce window produces
        exactly one render, not one per event."""
        from neony.application.elements import Button

        app = NeonApplication(Config(auto_render=True))
        fake = FakeWindow()
        btn = Button("x")
        tree = VStack(btn).build()
        _setup_entry(app, tree, fake)

        async def run():
            await app.render()  # mount rev 1
            # Four style-only events within the debounce window.  The
            # final state (hovered) differs from the base state, so the
            # coalesced render emits exactly one patch.
            for et in ("mouseover", "mouseout", "mouseover", "mouseover"):
                await _fire(app, btn._btn.key, et)
            await asyncio.sleep(0.05)
            return len(fake.patches)

        n = asyncio.run(run())
        assert n == 1, f"expected 1 coalesced patch, got {n}"

    def test_immediate_event_cancels_pending_deferred(self):
        """An immediate-path event arriving during the debounce window
        supersedes the pending deferred render."""
        app, fake, els = _build_app()
        inp = els["input"]

        async def run():
            await app.render()  # mount rev 1
            await _fire(app, inp._input.key, "focus")  # deferred → scheduled
            await _fire(app, inp._input.key, "input", "a")  # immediate → runs now
            assert len(fake.patches) == 1, "immediate event rendered synchronously"
            await asyncio.sleep(0.05)
            # The superseded deferred task must not emit a second patch —
            # its diff runs against the updated snapshot and finds nothing.
            return len(fake.patches)

        n = asyncio.run(run())
        assert n == 1, f"superseded deferred render emitted an extra patch (got {n})"


class TestEventBubbling:
    """Opt-in bubbling: events on handler-less children route to a
    `_bubble_events` ancestor (e.g. SidebarItem's icon/label spans)."""

    def _make_tree(self, bubble: bool):
        from neony.dom import Div, Span

        parent = Div(key="parent", container=[Span(key="child", container=["text"])])
        parent._bubble_events = bubble
        calls: list[str] = []
        parent.on_click(lambda e: calls.append(e.key))
        return parent, calls

    def test_child_event_bubbles_to_optin_ancestor(self):
        app = NeonApplication(Config(auto_render=True))
        fake = FakeWindow()
        parent, calls = self._make_tree(bubble=True)
        _setup_entry(app, parent, fake)

        # JS resolves the click to the child span's key; the span has no
        # handler, so the event bubbles to the _bubble_events parent.
        asyncio.run(_fire(app, "child", "click"))
        assert calls == ["child"], "bubbled event must keep the original element's key"
        # The parent's own key still routes directly (exact match path).
        asyncio.run(_fire(app, "parent", "click"))
        assert calls == ["child", "parent"]

    def test_child_event_dropped_without_optin(self):
        app = NeonApplication(Config(auto_render=True))
        fake = FakeWindow()
        parent, calls = self._make_tree(bubble=False)
        _setup_entry(app, parent, fake)

        asyncio.run(_fire(app, "child", "click"))
        assert calls == [], "no bubbling without _bubble_events"
        asyncio.run(_fire(app, "parent", "click"))
        assert calls == ["parent"]

    def test_bubbles_only_events_without_exact_match(self):
        """A child with its own handler keeps it — no double dispatch."""
        app = NeonApplication(Config(auto_render=True))
        fake = FakeWindow()

        from neony.dom import Div, Span

        calls: list[str] = []
        parent = Div(key="parent")
        parent._bubble_events = True
        child = Span(key="child", container=["text"])
        parent.container.append(child)
        child.on_click(lambda e: calls.append("child"))
        parent.on_click(lambda e: calls.append("parent"))
        _setup_entry(app, parent, fake)

        asyncio.run(_fire(app, "child", "click"))
        assert calls == ["child"], "child handler wins; parent must not double-fire"


class TestTypedState:
    """``state=`` accepts a custom dataclass / model; default stays SimpleNamespace."""

    def test_default_state_is_simplenamespace(self):
        app = NeonApplication(Config())
        assert isinstance(app.state, SimpleNamespace)

    def test_custom_state_object_is_used_as_is(self):
        from dataclasses import dataclass

        @dataclass
        class AppState:
            count: int = 0

        app = NeonApplication(Config(), state=AppState(count=3))
        assert app.state.count == 3
        app.state.count += 1  # mutable like the namespace default
        assert app.state.count == 4

    def test_launch_passes_state_through(self):
        from dataclasses import dataclass

        from neony.application import launch
        from neony.dom import Div

        @dataclass
        class AppState:
            name: str = "neony"

        state = AppState()
        captured: list = []
        original_init = NeonApplication.__init__

        def spy_init(self, config=None, *, state=None) -> None:
            captured.append(state)
            original_init(self, config, state=state)

        import unittest.mock

        with (
            unittest.mock.patch.object(NeonApplication, "__init__", spy_init),
            unittest.mock.patch.object(NeonApplication, "run", return_value=None),
        ):
            launch(Div(), state=state, width=100, height=100)
        assert captured == [state]


class TestHandlerIsolation:
    """One failing handler must not break the event chain."""

    def test_failing_handler_does_not_block_others(self):
        app = NeonApplication(Config(auto_render=True))
        fake = FakeWindow()

        calls: list[str] = []

        async def bad(_e: DomEvent) -> None:
            raise RuntimeError("boom")

        async def good(_e: DomEvent) -> None:
            calls.append("good")

        from neony.dom import Div

        div = Div()
        div._handlers["click"] = [bad, good]
        _setup_entry(app, div, fake)

        asyncio.run(_fire(app, div.key, "click"))
        assert calls == ["good"]


class TestReuseGuard:
    """Elements and components cannot be mounted into two trees — the
    framework raises with a clear message instead of silently corrupting
    ``_parent`` pointers, dirty propagation, and event bubbling."""

    def test_same_element_two_containers_raises(self):
        child = Div()
        first = Div()
        second = Div()
        first.container.append(child)
        with pytest.raises(RuntimeError, match="already mounted"):
            second.container.append(child)

    def test_component_build_twice_raises(self):
        btn = Button("x")
        btn.build()
        with pytest.raises(RuntimeError, match="only be called once"):
            btn.build()

    def test_shared_component_across_pages_raises(self):
        from neony.application import Page

        btn = Button("x")
        first = Page().add(btn)
        second = Page().add(btn)
        first.build()
        with pytest.raises(RuntimeError, match="only be called once"):
            second.build()

    def test_remove_from_wrong_container_raises(self):
        owner = Div()
        child = Div()
        owner.container.append(child)
        # Simulate a corrupted state where the element's parent pointer
        # was externally reassigned — removing it here would corrupt
        # the original tree.
        object.__setattr__(child, "_parent", Div())
        with pytest.raises(RuntimeError, match="not a child of this container"):
            owner.container.remove(child)
