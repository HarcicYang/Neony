"""Tests for signal bindings — bind_text / bind_style / bind_attr /
bind_visible on DOMElement and Component."""

import asyncio
from typing import Any, cast

from neony.dom import Div, Signal, Span, Styles


class TestBindText:
    def test_initial_value_applied(self):
        s = Signal("hello")
        el = Span()
        el.bind_text(s)
        assert el.container == ["hello"]

    def test_signal_change_updates_text(self):
        s = Signal("a")
        el = Span()
        el.bind_text(s)
        s.set("b")
        assert el.container == ["b"]

    def test_formatter(self):
        s = Signal(3)
        el = Span()
        el.bind_text(s, fmt=lambda n: f"x{n}")
        assert el.container == ["x3"]
        s.set(4)
        assert el.container == ["x4"]

    def test_change_marks_dirty(self):
        s = Signal(1)
        el = Span()
        el.bind_text(s)
        el._dirty = False
        s.set(2)
        assert el._dirty


class TestBindStyle:
    def test_initial_and_change(self):
        s = Signal("red")
        el = Div()
        el.bind_style(s, "color")
        assert el.styles.color == "red"
        s.set("blue")
        assert el.styles.color == "blue"

    def test_none_clears_property(self):
        s: Signal[str | None] = Signal("red")
        el = Div()
        el.bind_style(s, "color")
        s.set(None)
        assert el.styles.color is None

    def test_marks_dirty(self):
        s = Signal(1.0)
        el = Div()
        el.bind_style(s, "opacity")
        el._dirty = False
        s.set(0.5)
        assert el._dirty


class TestBindAttr:
    def test_initial_and_change(self):
        s = Signal("btn")
        el = Div()
        el.bind_attr(s, "title")
        assert el.args["title"] == "btn"
        s.set("other")
        assert el.args["title"] == "other"

    def test_value_is_stringified(self):
        s = Signal(42)
        el = Div()
        el.bind_attr(s, "data-n")
        assert el.args["data-n"] == "42"


class TestBindVisible:
    def test_falsy_hides_then_restores(self):
        s = Signal(True)
        el = Div(styles=Styles(display="flex"))
        el.bind_visible(s)
        assert el.styles.display == "flex"
        s.set(False)
        assert el.styles.display == "none"
        s.set(True)
        assert el.styles.display == "flex"  # original value restored

    def test_no_original_display_defaults_to_none(self):
        s = Signal(True)
        el = Div()
        el.bind_visible(s)
        assert el.styles.display is None
        s.set(False)
        assert el.styles.display == "none"


class TestUnbind:
    def test_unbind_stops_updates(self):
        s = Signal("a")
        el = Span()
        el.bind_text(s)
        el.unbind()
        s.set("b")
        assert el.container == ["a"]
        assert s._subs == set()  # effect fully unsubscribed


class TestMultipleBindings:
    def test_multiple_signals_one_element(self):
        text = Signal("hi")
        color = Signal("red")
        el = Div()
        el.bind_text(text)
        el.bind_style(color, "color")
        text.set("bye")
        color.set("blue")
        assert el.container == ["bye"]
        assert el.styles.color == "blue"


class TestComponentProxy:
    def test_text_component_binds(self):
        from neony.application.elements import Text

        s = Signal("start")
        t = Text("start")
        t.bind_text(s)
        assert t._root.container == ["start"]
        s.set("changed")
        assert t._root.container == ["changed"]

    def test_component_unbind(self):
        from neony.application.elements import Text

        s = Signal("a")
        t = Text("a")
        t.bind_text(s)
        t.unbind()
        s.set("b")
        assert t._root.container == ["a"]


class TestRenderIntegration:
    """Binding writes + app render: signal change outside any event
    handler schedules a render and produces the right patch."""

    def test_signal_write_renders_patch(self):
        from neony.application import Config, NeonApplication
        from neony.application.app import _Entry
        from neony.application.elements import Text
        from neony.dom.bridge import Neony

        class FakeWindow:
            def __init__(self) -> None:
                self.patches: list[dict] = []

            async def eval_js(self, script: str) -> str:
                return '{"ok": true}'

            async def emit(self, event: str, payload: dict) -> None:
                assert event == "neony:patch"
                self.patches.append(payload)

        app = NeonApplication(Config(auto_render=True))
        fake = FakeWindow()
        s = Signal(0)
        label = Text("0")
        label.bind_text(s)
        tree = label._root
        neony = Neony(name="neony", mount_selector=app.config.mount_selector)
        entry = _Entry(neony, tree)
        entry.window = cast(Any, fake)
        app._entries.append(entry)
        neony._win = cast(Any, fake)
        app._collect_handlers(neony, tree, 0)
        app._arm_render_request(tree, 0)

        async def run():
            await app.render()  # mount rev 1
            s.set(1)  # binding schedules a render via _render_request
            # let the scheduled chain run: binding effect → render task
            await asyncio.sleep(0.01)
            return [p["rev"] for p in fake.patches]

        revs = asyncio.run(run())
        assert revs == [2]
        # the patch carries the updated text
        texts = [op for op in fake.patches[-1]["ops"] if op["op"] == "set_text"]
        assert len(texts) == 1
        assert texts[0]["text"] == "1"
