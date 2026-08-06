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
from wryview import DragDropEvent

from neony.application import Config, NeonApplication
from neony.application._helpers import _Entry
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
    app._registered.append(set())
    app._collect_handlers(neony, tree, 0, app._registered[0])
    return neony


async def _fire(app: NeonApplication, key: str, event_type: str, value: Any = None, **extra: Any) -> None:
    await app._entries[0].neony._on_event(cast(Any, None), key=key, event_type=event_type, value=value, **extra)


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

            # user types → deferred render flushed after the debounce window
            await _fire(app, inp._input.key, "input", "a")
            await asyncio.sleep(0.05)
            # change event on blur → diff finds nothing → NO patch, NO rev bump
            await _fire(app, inp._input.key, "change", "a")
            # user types again → next patch must be rev 2 (continuous), not 3
            await _fire(app, inp._input.key, "input", "ab")
            await asyncio.sleep(0.05)

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
                await asyncio.sleep(0.05)  # flush each deferred render
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
            await asyncio.sleep(0.05)  # flush deferred render
            # focus leaves a → change with no diff
            await _fire(app, a._input.key, "change", "x")
            # type in b — must NOT resync
            await _fire(app, b._input.key, "input", "y")
            await asyncio.sleep(0.05)  # flush deferred render
            # echo state updated on the Python side
            assert echo_a.text == "Ax"
            assert echo_b.text == "By"
            return [p["rev"] for p in fake.patches]

        revs = asyncio.run(run())
        assert revs == [2, 3], f"expected continuous revs, got {revs}"
        assert fake.mount_calls == 1


class TestDeferredRender:
    """Hover / focus / blur / input events coalesce into one deferred render.

    Immediate-path events (click, change, keydown, ...) still render
    synchronously — the input tests in TestRevContinuity above now flush
    their deferred renders explicitly.
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
        from neony.application.elements import Button

        app = NeonApplication(Config(auto_render=True))
        fake = FakeWindow()
        btn = Button("go")
        tree = VStack(btn).build()
        _setup_entry(app, tree, fake)

        async def run():
            await app.render()  # mount rev 1
            await _fire(app, btn._btn.key, "focus")  # deferred → scheduled
            await _fire(app, btn._btn.key, "click")  # immediate → runs now
            assert len(fake.patches) == 1, "immediate event rendered synchronously"
            await asyncio.sleep(0.05)
            # The superseded deferred task must not emit a second patch —
            # its diff runs against the updated snapshot and finds nothing.
            return len(fake.patches)

        n = asyncio.run(run())
        assert n == 1, f"superseded deferred render emitted an extra patch (got {n})"

    def test_rapid_input_burst_coalesces(self):
        """Typing without pause coalesces into one deferred render, not
        one patch per keystroke."""
        app, fake, els = _build_app()
        inp = els["input"]

        async def run():
            await app.render()  # mount rev 1
            # Three keystrokes within the debounce window — the intermediate
            # renders are cancelled; only the final state lands.
            for ch in ("a", "ab", "abc"):
                await _fire(app, inp._input.key, "input", ch)
            assert fake.patches == [], "deferred renders must not fire synchronously"
            await asyncio.sleep(0.05)
            return len(fake.patches)

        n = asyncio.run(run())
        assert n == 1, f"expected 1 coalesced patch, got {n}"


class TestRichPayload:
    """Modifier keys / coordinates / delta / clipboard flow from the JS
    invocation through _on_event into the user's DomEvent."""

    @staticmethod
    def _keydown_app() -> tuple[NeonApplication, FakeWindow, str, list[DomEvent]]:
        """App wired to a raw keyed Div whose keydown handler records
        events.  Raw elements register handlers directly (components
        bind only their own events), so the whole tree can be collected
        in one pass."""
        from neony.dom import Div

        app = NeonApplication(Config(auto_render=True))
        fake = FakeWindow()
        div = Div(key="kbd")
        received: list[DomEvent] = []
        div.on_keydown(lambda e: received.append(e))
        _setup_entry(app, div, fake)
        return app, fake, div.key, received

    def test_modifier_keys_reach_handler(self):
        app, _fake, key, received = self._keydown_app()

        asyncio.run(_fire(app, key, "keydown", "s", ctrl_key=True, shift_key=True))

        assert len(received) == 1
        assert received[0].ctrl_key is True
        assert received[0].shift_key is True
        assert received[0].alt_key is False
        assert received[0].meta_key is False

    def test_coordinates_reach_handler(self):
        app, _fake, key, received = self._keydown_app()

        asyncio.run(_fire(app, key, "keydown", "s", x=42, y=17, offset_x=10, offset_y=5))

        assert received[0].x == 42
        assert received[0].y == 17
        assert received[0].offset_x == 10
        assert received[0].offset_y == 5

    def test_missing_rich_fields_default(self):
        """Events without rich payload fields keep the defaults — backward
        compatible with the old 4-field payload."""
        app, _fake, key, received = self._keydown_app()

        asyncio.run(_fire(app, key, "keydown", "s"))

        evt = received[0]
        assert evt.ctrl_key is False
        assert evt.x is None
        assert evt.delta_x is None
        assert evt.clipboard_text is None

    def test_numeric_coords_pass_lumiview_strict_conversion(self):
        """Browser coordinates arrive as JSON integers (clientX: 123), but
        lumiview converts payload values with strict type matching.  The
        command signature must accept ints or every mouse event would be
        rejected at the bridge (gallery regression: clicks dead)."""
        import typing

        from lumiview._binding import _converter, bind_arguments
        from lumiview.scope import Command, Scope

        # The command system registers the *bound* method (no `self`),
        # exactly like ``self.command(self._on_event, ...)`` in __init__.
        command_fn = Neony(name="neony")._on_event
        hints = typing.get_type_hints(command_fn)
        for value in (123, 12.5):
            for name in ("x", "y", "offset_x", "offset_y", "delta_x", "delta_y"):
                converted = _converter.structure(value, hints[name])
                assert converted == value, f"{name}={value!r} failed strict conversion"

        # The whole JS payload shape binds without error...
        payload = {
            "key": "btn",
            "event_type": "click",
            "value": None,
            "x": 123,
            "y": 45,
            "offset_x": 12,
            "offset_y": 9,
        }
        bound = bind_arguments(
            Command(fn=command_fn, name="event", scope=Scope("test")),
            payload,
            window=None,
        )
        assert bound["x"] == 123
        assert bound["offset_y"] == 9
        # ...and the bound kwargs invoke the command (no invalid_argument).
        assert bound["key"] == "btn"
        assert bound["event_type"] == "click"

    def test_clipboard_data_reaches_handler(self):
        app = NeonApplication(Config(auto_render=True))
        fake = FakeWindow()
        div = Div(key="paste-target")
        received: list[DomEvent] = []
        div.on_paste(lambda e: received.append(e))
        _setup_entry(app, div, fake)

        asyncio.run(
            _fire(
                app,
                div.key,
                "paste",
                None,
                clipboard_text="hi",
                clipboard_html="<b>hi</b>",
            )
        )

        assert len(received) == 1
        assert received[0].clipboard_text == "hi"
        assert received[0].clipboard_html == "<b>hi</b>"

    def test_drop_files_reach_handler(self):
        """Dropped files flow from the JS payload through _on_event into
        DomEvent.drop_files (a list of {name, path, size, type} dicts)."""
        app = NeonApplication(Config(auto_render=True))
        fake = FakeWindow()
        div = Div(key="drop-zone")
        received: list[DomEvent] = []
        div.on_drop(lambda e: received.append(e))
        _setup_entry(app, div, fake)

        files = [
            {"name": "a.png", "path": "/home/user/a.png", "size": 1024, "type": "image/png"},
            {"name": "b.txt", "path": "", "size": 12, "type": "text/plain"},
        ]
        asyncio.run(_fire(app, div.key, "drop", None, drop_files=files))

        assert len(received) == 1
        assert received[0].drop_files == files
        assert received[0].drop_files is not None
        assert received[0].drop_files[0]["path"] == "/home/user/a.png"


class TestNativeDropBackfill:
    """Empty ``path`` entries in drop_files are backfilled from the
    window's native drag-drop handler (WebKitGTK ≥ 2.52 removed
    ``File.path``) — matched by base name, positionally as a fallback."""

    def _drop_app(self) -> tuple[NeonApplication, FakeWindow, Div, list[DomEvent]]:
        app = NeonApplication(Config(auto_render=True))
        fake = FakeWindow()
        div = Div(key="drop-zone")
        received: list[DomEvent] = []
        div.on_drop(lambda e: received.append(e))
        _setup_entry(app, div, fake)
        return app, fake, div, received

    def test_paths_backfilled_by_basename(self):
        app, _fake, div, received = self._drop_app()
        app._entries[0].neony.native_drop_paths[:] = ["/home/user/a.png", "/tmp/b.txt"]

        files = [
            {"name": "b.txt", "path": "", "size": 12, "type": "text/plain"},
            {"name": "a.png", "path": "", "size": 1024, "type": "image/png"},
        ]
        asyncio.run(_fire(app, div.key, "drop", None, drop_files=files))

        assert received[0].drop_files is not None
        paths = [f["path"] for f in received[0].drop_files]
        assert paths == ["/tmp/b.txt", "/home/user/a.png"]

    def test_positional_fallback_when_names_differ(self):
        """No base-name match and equal counts → paths fill in drop order
        (the JS File.name can be an alias of the real file name)."""
        app, _fake, div, received = self._drop_app()
        app._entries[0].neony.native_drop_paths[:] = ["/data/photo 1.jpg", "/data/notes.txt"]

        files = [
            {"name": "photo", "path": "", "size": 100, "type": "image/jpeg"},
            {"name": "notes", "path": "", "size": 200, "type": "text/plain"},
        ]
        asyncio.run(_fire(app, div.key, "drop", None, drop_files=files))

        assert received[0].drop_files is not None
        paths = [f["path"] for f in received[0].drop_files]
        assert paths == ["/data/photo 1.jpg", "/data/notes.txt"]

    def test_existing_paths_left_untouched(self):
        """WebView2 exposes File.path — backfill must not overwrite."""
        app, _fake, div, received = self._drop_app()
        app._entries[0].neony.native_drop_paths[:] = ["/native/a.png"]

        files = [{"name": "a.png", "path": "/real/a.png", "size": 1, "type": "image/png"}]
        asyncio.run(_fire(app, div.key, "drop", None, drop_files=files))

        assert received[0].drop_files is not None
        assert received[0].drop_files[0]["path"] == "/real/a.png"

    def test_no_native_paths_leaves_empty(self):
        app, _fake, div, received = self._drop_app()

        files = [{"name": "a.png", "path": "", "size": 1, "type": "image/png"}]
        asyncio.run(_fire(app, div.key, "drop", None, drop_files=files))

        assert received[0].drop_files is not None
        assert received[0].drop_files[0]["path"] == ""


class TestNativeDragDropHandler:
    """NeonApplication._make_drag_drop_handler: native takeover of file
    drops.  WebKitGTK delivers an *empty* JS drop when the handler is
    installed (verified in the real environment), so lumiview's
    ``WindowEvent.DragEvent`` (dev3) carries the real paths and Neony
    re-dispatches the file list from Python."""

    def _handler(self) -> tuple[NeonApplication, Neony]:
        app = NeonApplication(Config())
        neony = Neony(name="neony", mount_selector="body")
        app._entries.append(_Entry(neony, Div()))
        return app, neony

    def _drag(self, app: NeonApplication, kind, paths, position=(0, 0)) -> None:
        """Run the DragEvent handler (async) with a real event object."""
        handler = app._make_drag_drop_handler(app._entries[0])
        from lumiview import WindowEvent

        asyncio.run(handler(WindowEvent.DragEvent(kind=kind, paths=paths, position=position)))

    def test_drop_records_paths_and_builds_file_info(self):
        app, neony = self._handler()

        self._drag(app, DragDropEvent.Drop, ["/home/user/a.png", "/tmp/b.txt"], (100, 200))

        assert neony.native_drop_paths == ["/home/user/a.png", "/tmp/b.txt"]

    def test_enter_records_paths(self):
        app, neony = self._handler()

        self._drag(app, DragDropEvent.Enter, ["/home/user/a.png"])

        assert neony.native_drop_paths == ["/home/user/a.png"]

    def test_motion_events_leave_paths_untouched(self):
        app, neony = self._handler()
        self._drag(app, DragDropEvent.Enter, ["/home/user/a.png"])

        self._drag(app, DragDropEvent.Over, [])

        assert neony.native_drop_paths == ["/home/user/a.png"]

    def test_file_info_from_real_path(self, tmp_path):
        from neony.application._helpers import _file_info

        target = tmp_path / "photo 1.png"
        target.write_bytes(b"12345")

        info = _file_info(str(target))

        assert info == {
            "name": "photo 1.png",
            "path": str(target),
            "size": 5,
            "type": "image/png",
        }

    def test_dispatch_native_drop_hit_tests_and_delivers(self):
        """_dispatch_native_drop resolves the element under the pointer
        (eval_js returns the JSON-quoted key) and dispatches a drop event
        with the real file info."""
        app = NeonApplication(Config(auto_render=True))
        fake = FakeWindow()
        div = Div(key="drop-zone")
        received: list[DomEvent] = []
        div.on_drop(lambda e: received.append(e))
        _setup_entry(app, div, fake)
        # The hit-test script's result arrives JSON-quoted, like the
        # real WebKitGTK backend (key "drop-zone").
        scripts: list[str] = []

        async def hit_test_eval(script: str) -> str:
            scripts.append(script)
            return '"drop-zone"'

        fake.eval_js = hit_test_eval  # type: ignore[method-assign]

        files = [{"name": "a.png", "path": "/home/user/a.png", "size": 5, "type": "image/png"}]
        asyncio.run(app._dispatch_native_drop(app._entries[0], files, (10, 20)))

        assert len(received) == 1
        assert received[0].drop_files is not None
        assert received[0].drop_files[0]["path"] == "/home/user/a.png"
        assert "elementFromPoint(10, 20)" in scripts[0]


class TestComponentEventWiring:
    """Component.on() lazily wires DOM event types its internals don't
    bind — on_keydown on an Input must reach callbacks (regression: the
    callback was stored but nothing forwarded keydown through it)."""

    def test_component_keydown_reaches_callbacks(self):
        from neony.application.elements import Input

        app = NeonApplication(Config(auto_render=True))
        fake = FakeWindow()
        inp = Input(placeholder="x")
        received: list[DomEvent] = []
        inp.on_keydown(lambda e: received.append(e))
        _setup_entry(app, inp.build(), fake)

        asyncio.run(_fire(app, inp._root.key, "keydown", "s", ctrl_key=True))

        assert len(received) == 1
        assert received[0].ctrl_key is True

    def test_bound_event_types_do_not_double_fire(self):
        """Focus is wired by Input itself — a registered on_focus
        callback must fire exactly once, not once per wiring."""
        from neony.application.elements import Input

        app = NeonApplication(Config(auto_render=True))
        fake = FakeWindow()
        inp = Input(placeholder="x")
        calls: list[str] = []
        inp.on_focus(lambda e: calls.append("focus"))
        _setup_entry(app, inp.build(), fake)

        asyncio.run(_fire(app, inp._root.key, "focus"))

        assert calls == ["focus"]

    def test_pseudo_events_do_not_wire_the_root(self):
        """Non-DOM types (TitleBar's "close") never get a root wire."""
        from neony.application.elements import TitleBar

        titlebar = TitleBar("t")
        titlebar.on_close(lambda: None)
        assert "close" not in titlebar._raw_wired


class TestEventBubbling:
    """Opt-in bubbling: events on handler-less children route to a
    `bubble_events` ancestor (e.g. SidebarItem's icon/label spans)."""

    def _make_tree(self, bubble: bool):
        from neony.dom import Div, Span

        parent = Div(key="parent", container=[Span(key="child", container=["text"])])
        parent.bubble_events = bubble
        calls: list[str] = []
        parent.on_click(lambda e: calls.append(e.key))
        return parent, calls

    def test_child_event_bubbles_to_optin_ancestor(self):
        app = NeonApplication(Config(auto_render=True))
        fake = FakeWindow()
        parent, calls = self._make_tree(bubble=True)
        _setup_entry(app, parent, fake)

        # JS resolves the click to the child span's key; the span has no
        # handler, so the event bubbles to the bubble_events parent.
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
        assert calls == [], "no bubbling without bubble_events"
        asyncio.run(_fire(app, "parent", "click"))
        assert calls == ["parent"]

    def test_bubbles_even_when_target_has_handler(self):
        """A child's own handler fires first, then the event bubbles to
        the nearest bubble_events ancestor — window-level listeners
        (page key handlers, shortcuts) must see keys typed in inputs
        that handle their own events."""
        app = NeonApplication(Config(auto_render=True))
        fake = FakeWindow()

        from neony.dom import Div, Span

        calls: list[str] = []
        parent = Div(key="parent")
        parent.bubble_events = True
        child = Span(key="child", container=["text"])
        parent.container.append(child)
        child.on_click(lambda e: calls.append("child"))
        parent.on_click(lambda e: calls.append("parent"))
        _setup_entry(app, parent, fake)

        asyncio.run(_fire(app, "child", "click"))
        assert calls == ["child", "parent"], "target handler then bubbled ancestor"
        # The parent's own key routes directly — no duplicate bubble pass.
        asyncio.run(_fire(app, "parent", "click"))
        assert calls == ["child", "parent", "parent"]


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

    def test_sync_handler_runs_and_renders(self):
        """A plain (sync) raw-element handler must not crash the wrapper
        (regression: ``await fn(evt)`` raised TypeError on sync handlers,
        so the handler ran but auto-render was skipped — the UI never
        refreshed)."""
        app = NeonApplication(Config(auto_render=True))
        fake = FakeWindow()
        calls: list[str] = []

        from neony.dom import Div

        div = Div(key="btn", container=["before"])
        div.on_click(lambda e: (calls.append("clicked"), div.container.__setitem__(0, "after")))
        _setup_entry(app, div, fake)

        async def run():
            await app.render()  # mount rev 1
            await _fire(app, div.key, "click")
            return [p["rev"] for p in fake.patches]

        revs = asyncio.run(run())

        assert calls == ["clicked"]
        assert revs == [2], "auto-render must run after a sync handler (no TypeError)"

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


class TestPointermove:
    """Pointermove events carry movement deltas and pointer type, and
    ride the deferred render path (they fire at frame rate)."""

    @staticmethod
    def _pointermove_app() -> tuple[NeonApplication, FakeWindow, str, list[DomEvent]]:
        from neony.dom import Div

        app = NeonApplication(Config(auto_render=True))
        fake = FakeWindow()
        div = Div(key="drag-area", container=["label"])
        received: list[DomEvent] = []

        def on_move(e: DomEvent) -> None:
            # Mutate the DOM (like a drag label would), so the deferred
            # render diff produces a real patch.
            received.append(e)
            div.container[0] = f"({e.movement_x}, {e.movement_y})"

        div.on_pointermove(on_move)
        _setup_entry(app, div, fake)
        return app, fake, div.key, received

    def test_movement_delta_reaches_handler(self):
        """movement_x / movement_y / pointer_type flow through to the
        handler's DomEvent."""
        app, _fake, key, received = self._pointermove_app()

        asyncio.run(
            _fire(
                app,
                key,
                "pointermove",
                x=100,
                y=200,
                movement_x=5,
                movement_y=-3,
                pointer_type="mouse",
            )
        )

        assert len(received) == 1
        evt = received[0]
        assert evt.x == 100
        assert evt.y == 200
        assert evt.movement_x == 5
        assert evt.movement_y == -3
        assert evt.pointer_type == "mouse"

    def test_missing_pointer_fields_default_to_none(self):
        """Non-pointermove events don't carry movement or pointer_type —
        the defaults must stay None for backward compatibility."""
        from neony.dom import Div

        app = NeonApplication(Config(auto_render=True))
        fake = FakeWindow()
        div = Div(key="btn")
        received: list[DomEvent] = []
        div.on_click(lambda e: received.append(e))
        _setup_entry(app, div, fake)

        asyncio.run(_fire(app, div.key, "click", None, x=42, y=17))

        evt = received[0]
        assert evt.movement_x is None
        assert evt.movement_y is None
        assert evt.pointer_type is None

    def test_pointermove_is_deferred(self):
        """Pointermove must not render synchronously — it rides the
        deferred path with one frame of coalescing."""
        app, fake, key, _received = self._pointermove_app()

        async def run():
            await app.render()  # mount rev 1
            await _fire(app, key, "pointermove", None, x=100, y=200, movement_x=1, movement_y=0, pointer_type="mouse")
            assert fake.patches == [], "pointermove must not render synchronously"
            await asyncio.sleep(0.05)  # > debounce window (16ms)
            return len(fake.patches)

        n = asyncio.run(run())
        assert n == 1, f"expected 1 deferred patch, got {n}"

    def test_pointermove_burst_coalesces(self):
        """A burst of pointermoves within the debounce window produces
        exactly one render, not one per event."""
        app, fake, key, _received = self._pointermove_app()

        async def run():
            await app.render()  # mount rev 1
            for i in range(4):
                await _fire(
                    app,
                    key,
                    "pointermove",
                    None,
                    x=100 + i,
                    y=200 + i,
                    movement_x=1,
                    movement_y=1,
                    pointer_type="mouse",
                )
            await asyncio.sleep(0.05)
            return len(fake.patches)

        n = asyncio.run(run())
        assert n == 1, f"expected 1 coalesced patch, got {n}"


class TestTransitionHooks:
    """transitionend / animationstart / animationend carry the CSS
    property or animation name plus the elapsed time."""

    @staticmethod
    def _event_app(event_type: str) -> tuple[NeonApplication, FakeWindow, str, list[DomEvent]]:
        from neony.dom import Div

        app = NeonApplication(Config(auto_render=True))
        fake = FakeWindow()
        div = Div(key="animated")
        received: list[DomEvent] = []
        div.on(event_type, lambda e: received.append(e))
        _setup_entry(app, div, fake)
        return app, fake, div.key, received

    def test_transitionend_carries_property_and_time(self):
        app, _fake, key, received = self._event_app("transitionend")

        asyncio.run(_fire(app, key, "transitionend", None, transition_property="opacity", elapsed_time=0.15))

        assert len(received) == 1
        evt = received[0]
        assert evt.transition_property == "opacity"
        assert evt.elapsed_time == 0.15

    def test_animationend_carries_name_and_time(self):
        app, _fake, key, received = self._event_app("animationend")

        asyncio.run(_fire(app, key, "animationend", None, animation_name="spin", elapsed_time=2.0))

        assert len(received) == 1
        evt = received[0]
        assert evt.animation_name == "spin"
        assert evt.elapsed_time == 2.0

    def test_animationstart_carries_name(self):
        app, _fake, key, received = self._event_app("animationstart")

        asyncio.run(_fire(app, key, "animationstart", None, animation_name="spin"))

        assert len(received) == 1
        evt = received[0]
        assert evt.animation_name == "spin"
        assert evt.elapsed_time is None

    def test_transition_fields_default_to_none(self):
        """Non-transition events carry no transition/animation payload."""
        from neony.dom import Div

        app = NeonApplication(Config(auto_render=True))
        fake = FakeWindow()
        div = Div(key="btn")
        received: list[DomEvent] = []
        div.on_click(lambda e: received.append(e))
        _setup_entry(app, div, fake)

        asyncio.run(_fire(app, div.key, "click", None, x=42, y=17))

        evt = received[0]
        assert evt.transition_property is None
        assert evt.elapsed_time is None
        assert evt.animation_name is None


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


class TestAnimationStyle:
    """Animation styles flow through mount and the direct-patch path."""

    def test_animation_style_in_mount_payload(self):
        """The mount message carries the flattened animation shorthand."""
        from neony.dom import Animation, Styles

        capture: dict = {}

        class CaptureWindow(FakeWindow):
            async def eval_js(self, script: str) -> str:
                capture["script"] = script
                return await super().eval_js(script)

        app = NeonApplication(Config(auto_render=True))
        fake = CaptureWindow()
        div = Div(key="d", container=["spin me"], styles=Styles())
        div.styles.animation = Animation(name="spin", duration="2s", iteration_count="infinite")
        tree = VStack(div).build()
        _setup_entry(app, tree, fake)

        async def run() -> None:
            await app.render()

        asyncio.run(run())
        assert '"animation":"spin 2s ease infinite"' in capture["script"]


class TestLateElementHandlers:
    """Elements created after the startup sweep must still receive events.

    Dynamic content (ComboBox suggestion rows, future overlays, ...) is
    appended to the tree inside event handlers — those elements were not
    in the startup handler collection, so the bridge dropped their
    events entirely.  The render loop re-sweeps and registers new
    (key, event_type) pairs; this locks that in.
    """

    def test_combo_popup_rows_receive_clicks_after_render(self):
        from neony.application.elements import ComboBox

        app = NeonApplication(Config(auto_render=True))
        fake = FakeWindow()
        cb = ComboBox(options=["work", "personal"])
        tree = cb.build()
        _setup_entry(app, tree, fake)

        async def run() -> None:
            await app.render()  # mount
            # typing rebuilds the popup rows (created post-startup)
            await _fire(app, cb._input.key, "input", "wo")
            await asyncio.sleep(0.05)  # flush the deferred render
            row = cb._rows[0]
            assert row.key in app._entries[0].neony._key_map
            fired: list = []
            cb.on_change(lambda e: fired.append(e.value))
            await _fire(app, row.key, "click")
            assert fired == ["work"]
            assert cb.value == "work"

        asyncio.run(run())

    def test_handlers_are_not_double_registered(self):
        """The render re-sweep must not re-register startup handlers —
        the same (key, type) pair would double-fire."""
        from neony.application.elements import Button

        app = NeonApplication(Config(auto_render=True))
        fake = FakeWindow()
        btn = Button("x")
        tree = btn.build()
        _setup_entry(app, tree, fake)

        async def run() -> None:
            await app.render()  # mount → re-sweep
            await app.render()  # empty re-render → re-sweep again
            fired: list = []
            btn.on_click(lambda e: fired.append(1))
            await _fire(app, btn._btn.key, "click")
            assert fired == [1]

        asyncio.run(run())


class TestComboPickRenders:
    """The auto-complete write-back must reach the DOM through the
    render pipeline — a pick that only updates Python state would leave
    the input showing the pre-pick text."""

    def test_pick_sends_input_value_patch(self):
        from neony.application.elements import ComboBox

        app = NeonApplication(Config(auto_render=True))
        fake = FakeWindow()
        cb = ComboBox(options=["work", "personal"])
        tree = cb.build()
        _setup_entry(app, tree, fake)

        async def run() -> None:
            await app.render()  # mount rev 1
            await _fire(app, cb._input.key, "input", "wo")
            await asyncio.sleep(0.05)  # flush the deferred render
            # Enter picks "work" — the follow-up render must patch the
            # input's value attribute
            await _fire(app, cb._input.key, "keydown", "Enter")
            assert cb.value == "work"
            patch = fake.patches[-1]
            assert patch["rev"] == fake.patches[-1]["rev"]
            value_ops = [op for op in patch["ops"] if op.get("op") == "update_attrs" and op.get("key") == cb._input.key]
            assert value_ops, f"no value patch for the input in {patch['ops']}"
            assert value_ops[-1]["set"].get("value") == "work"

        asyncio.run(run())

    def test_pick_value_reaches_the_serialized_tree(self):
        """After a pick, a re-render (any event) keeps the picked value
        in the tree — the diff must not revert it."""
        from neony.application.elements import ComboBox

        app = NeonApplication(Config(auto_render=True))
        fake = FakeWindow()
        cb = ComboBox(options=["work", "personal"])
        tree = cb.build()
        _setup_entry(app, tree, fake)

        async def run() -> None:
            await app.render()
            await _fire(app, cb._input.key, "input", "wo")
            await asyncio.sleep(0.05)
            await _fire(app, cb._input.key, "keydown", "Enter")
            # any further event-driven render keeps value="work"
            node = tree.to_node()
            from neony.dom import NodeDescriptor

            def find(n: NodeDescriptor, key: str) -> NodeDescriptor | None:
                if n.key == key:
                    return n
                for c in n.children:
                    found = find(c, key)
                    if found:
                        return found
                return None

            inp = find(node, cb._input.key)
            assert inp is not None
            assert inp.attrs["value"] == "work"

        asyncio.run(run())
