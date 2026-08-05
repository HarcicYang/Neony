"""Tests for the style/attr direct-patch fast path.

Pure style/attr changes must bypass ``to_node()`` serialization and the
diff engine — emitting ``update_styles``/``update_attrs`` patches
directly from the snapshot cache.  Structural changes (container, text,
key) fall through to the full path.
"""

import asyncio
from typing import Any, cast

from neony.application import Config, NeonApplication
from neony.application.app import _Entry
from neony.application.elements import Button, Input, VStack
from neony.dom import Color, Div, DOMElement, Span, Styles
from neony.dom.bridge import Neony
from neony.dom.reactive import Signal


def _spy_to_node():
    """Patch ``DOMElement.to_node`` with a recording wrapper that still
    runs the real serialization.  Returns ``(patcher, calls)`` — *calls*
    holds each serialized element's key."""
    real = DOMElement.to_node
    calls: list[str] = []

    def spy(self, snapshot_cache=None):
        calls.append(self.key)
        return real(self, snapshot_cache)

    from unittest.mock import patch

    return patch.object(DOMElement, "to_node", new=spy), calls


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
    app._arm_render_request(tree, 0)  # signal bindings schedule renders
    return neony


async def _fire(app: NeonApplication, key: str, event_type: str, value: Any = None) -> None:
    await app._entries[0].neony._on_event(cast(Any, None), key=key, event_type=event_type, value=value)


def _build_app(*elements) -> tuple[NeonApplication, FakeWindow, DOMElement]:
    app = NeonApplication(Config(auto_render=True))
    fake = FakeWindow()
    tree = VStack(*elements).build()
    _setup_entry(app, tree, fake)
    return app, fake, tree


class TestStyleDirectPatch:
    def test_style_only_change_skips_serialization_and_diff(self):
        """Hover produces update_styles directly — to_node() never runs."""
        btn = Button("hover")
        app, fake, _ = _build_app(btn)

        async def run():
            await app.render()  # mount
            patcher, calls = _spy_to_node()
            with patcher:
                await _fire(app, btn._btn.key, "mouseover")
                await asyncio.sleep(0.05)  # deferred render (16ms debounce)
                assert calls == []
            return fake.patches[-1]

        msg = asyncio.run(run())
        assert msg["rev"] == 2
        assert [op["op"] for op in msg["ops"]] == ["update_styles"]
        assert msg["ops"][0]["key"] == btn._btn.key
        assert fake.mount_calls == 1  # no resync

    def test_attr_only_change_uses_direct_patch(self):
        """args assignment produces update_attrs directly."""
        div = Div(key="d", container=["text"])
        app, fake, _ = _build_app(div)

        async def run():
            await app.render()  # mount
            patcher, calls = _spy_to_node()
            with patcher:
                div.args = {"title": "hello"}
                await app.render()
                assert calls == []
            return fake.patches[-1]

        msg = asyncio.run(run())
        assert msg["rev"] == 2
        assert [op["op"] for op in msg["ops"]] == ["update_attrs"]
        assert msg["ops"][0]["set"] == {"title": "hello"}

    def test_mixed_change_falls_through_to_full_diff(self):
        """Style + container change on the same element forces full path."""
        btn = Button("x")
        app, fake, _ = _build_app(btn)

        async def run():
            await app.render()  # mount
            btn._btn.styles = Styles(opacity=0.5)
            btn._btn.container = ["new text"]
            patcher, calls = _spy_to_node()
            with patcher:
                await app.render()
                assert len(calls) == 1
            return fake.patches[-1]

        msg = asyncio.run(run())
        ops = {op["op"] for op in msg["ops"]}
        assert {"update_styles", "set_text"} <= ops

    def test_structural_change_in_sibling_forces_full_path(self):
        """A structural change in one element forces the full path for all."""
        a, b = Button("a"), Button("b")
        app, fake, _ = _build_app(a, b)

        async def run():
            await app.render()  # mount
            a._btn.styles = Styles(opacity=0.5)  # style-only
            b._btn.container = ["changed"]  # structural sibling
            patcher, calls = _spy_to_node()
            with patcher:
                await app.render()
                assert len(calls) == 1
            return len(fake.patches)

        assert asyncio.run(run()) == 1  # mount emits no patch

    def test_multiple_style_only_elements_coalesce_into_one_message(self):
        """Two buttons hovered within the debounce window: one message,
        one update_styles per button."""
        a, b = Button("a"), Button("b")
        app, fake, _ = _build_app(a, b)

        async def run():
            await app.render()  # mount
            await _fire(app, a._btn.key, "mouseover")
            await _fire(app, b._btn.key, "mouseover")
            await asyncio.sleep(0.05)
            return len(fake.patches)

        assert asyncio.run(run()) == 1  # mount emits no patch — just the coalesced one
        ops = fake.patches[-1]["ops"]
        assert len(ops) == 2
        assert {op["key"] for op in ops} == {a._btn.key, b._btn.key}

    def test_direct_patch_updates_snapshot_cache(self):
        """The cached snapshot reflects the patch, so a later full render
        does not re-emit the same style change."""
        btn = Button("x")
        app, fake, _ = _build_app(btn)
        neony = app._entries[0].neony

        async def run():
            await app.render()  # mount
            await _fire(app, btn._btn.key, "mouseover")
            await asyncio.sleep(0.05)
            # snapshot cache now carries the hovered styles
            cached = neony._snapshots[btn._btn.key]
            assert cached.styles["opacity"] == "0.92"
            # structural change elsewhere forces a full render — the
            # hovered style must not re-emit
            btn._btn.container = ["new text"]
            await app.render()
            ops = fake.patches[-1]["ops"]
            assert not any(op["op"] == "update_styles" for op in ops)

        asyncio.run(run())

    def test_empty_style_diff_no_rev_bump(self):
        """Setting an equal Styles object produces no patch, no rev bump."""
        btn = Button("x")
        app, fake, _ = _build_app(btn)
        neony = app._entries[0].neony

        async def run():
            await app.render()  # mount rev 1
            btn._btn.styles = btn._btn.styles.model_copy()  # equal
            await app.render()
            return neony._rev, fake.patches

        rev, patches = asyncio.run(run())
        assert rev == 1  # no rev bump, no message, no resync
        assert patches == []
        assert fake.mount_calls == 1

    def test_rev_continuity_alternating_fast_and_full_path(self):
        """Style-only and structural renders interleave without gaps."""
        btn = Button("x")
        app, fake, _ = _build_app(btn)

        async def run():
            await app.render()  # mount rev 1
            await _fire(app, btn._btn.key, "mouseover")  # direct
            await asyncio.sleep(0.05)
            btn._btn.container = ["text"]  # structural
            await app.render()
            await _fire(app, btn._btn.key, "mouseout")  # direct
            await asyncio.sleep(0.05)
            return [p["rev"] for p in fake.patches]

        assert asyncio.run(run()) == [2, 3, 4]
        assert fake.mount_calls == 1

    def test_deeply_nested_style_change_direct_patched(self):
        """A grandchild style change patches only that element."""
        inner = Span(key="deep", text="s", styles=Styles(color=Color(name="red")))
        mid = Div(key="mid", container=[inner])
        root = Div(key="root", container=[mid])
        app = NeonApplication(Config(auto_render=True))
        fake = FakeWindow()
        _setup_entry(app, root, fake)

        async def run():
            await app.render()  # mount
            patcher, calls = _spy_to_node()
            with patcher:
                inner.styles = Styles(color=Color(name="blue"))
                await app.render()
                assert calls == []
            return fake.patches[-1]

        msg = asyncio.run(run())
        assert msg["rev"] == 2
        assert len(msg["ops"]) == 1
        assert msg["ops"][0]["op"] == "update_styles"
        assert msg["ops"][0]["key"] == "deep"
        assert msg["ops"][0]["set"]["color"] == "blue"

    def test_vendor_prefixes_in_direct_patch(self):
        """backdrop-filter / user-select mirror their prefixed variants."""
        div = Div(key="d")
        app, fake, _ = _build_app(div)

        async def run():
            await app.render()  # mount
            div.styles = Styles(backdrop_filter="blur(8px)", user_select="none")
            await app.render()
            return fake.patches[-1]["ops"][0]["set"]

        set_dict = asyncio.run(run())
        assert set_dict["backdrop-filter"] == "blur(8px)"
        assert set_dict["-webkit-backdrop-filter"] == "blur(8px)"
        assert set_dict["user-select"] == "none"
        assert set_dict["-webkit-user-select"] == "none"
        assert set_dict["-moz-user-select"] == "none"

    def test_first_render_never_direct_patches(self):
        """The mount path always goes through full serialization."""
        btn = Button("x")
        app, fake, _ = _build_app(btn)

        async def run():
            patcher, calls = _spy_to_node()
            with patcher:
                await app.render()
                assert len(calls) == 1
            return fake.mount_calls

        assert asyncio.run(run()) == 1

    def test_signal_binding_style_change_direct_patched(self):
        """bind_style() writes take the direct-patch path."""
        div = Div(key="d")
        app, fake, _ = _build_app(div)
        sig = Signal(Color(var="--color-accent"))
        div.bind_style(sig, "background_color")

        async def run():
            await app.render()  # mount (binding already applied once)
            patcher, calls = _spy_to_node()
            with patcher:
                sig.set(Color(var="--color-danger"))
                await asyncio.sleep(0.05)  # effect flush + render task
                assert calls == []
            return fake.patches[-1]

        msg = asyncio.run(run())
        assert msg["rev"] == 2
        assert msg["ops"][0]["op"] == "update_styles"
        assert msg["ops"][0]["set"]["background-color"] == "var(--color-danger)"

    def test_component_focus_direct_patched(self):
        """Component focus feedback (Input) still direct-patches."""
        inp = Input(placeholder="name")
        app, fake, _ = _build_app(inp)

        async def run():
            await app.render()  # mount
            patcher, calls = _spy_to_node()
            with patcher:
                await _fire(app, inp._input.key, "focus")
                await asyncio.sleep(0.05)
                assert calls == []
            return fake.patches[-1]

        msg = asyncio.run(run())
        assert msg["rev"] == 2
        assert msg["ops"][0]["op"] == "update_styles"


class TestAnimationDirectPatch:
    """Animation style changes take the same direct-patch fast path."""

    def test_animation_change_uses_direct_patch(self):
        """Changing only the animation style emits update_styles — no
        serialization, no diff engine."""
        from neony.dom import Animation

        div = Div(key="d", container=["x"])
        app, fake, _ = _build_app(div)

        async def run() -> dict:
            await app.render()  # mount (rev 1)
            div.styles.animation = Animation(name="fade", duration="0.5s")
            patcher, calls = _spy_to_node()
            with patcher:
                await app.render()
                assert calls == []  # fast path — no serialization
            return fake.patches[-1]

        msg = asyncio.run(run())
        assert msg["rev"] == 2
        assert [op["op"] for op in msg["ops"]] == ["update_styles"]
        assert msg["ops"][0]["set"] == {"animation": "fade 0.5s ease"}
