"""Streaming text: append-aware patches, append_text/stream APIs, Markdown.

The append path keeps streaming text cheap: a pure text extension ships
only the delta (``AppendTextPatch``), and the Markdown component pushes
its raw source through internal JS commands instead of the diff.
"""

import asyncio
import json
import re
from typing import Any, cast

import pytest

from neony.application import Config, NeonApplication
from neony.application._helpers import _Entry
from neony.application.elements import Markdown, MessageBubble, NoticeBubble, Text
from neony.application.markdown_css import MARKDOWN_CSS
from neony.dom import Br, Color, Div, DOMElement, Signal, Span
from neony.dom.bridge import Neony


class RecordingWindow:
    """Minimal lumiview Window stand-in that records both channels."""

    def __init__(self) -> None:
        self.patches: list[dict] = []
        self.scripts: list[str] = []

    async def eval_js(self, script: str) -> str:
        self.scripts.append(script)
        return '{"ok": true}'

    async def emit(self, event: str, payload: dict) -> None:
        assert event == "neony:patch"
        self.patches.append(payload)


def _setup(app: NeonApplication, tree: DOMElement, fake: RecordingWindow) -> Neony:
    """Simulate run()'s per-window setup without starting LumiView."""
    neony = Neony(name="neony", mount_selector=app.config.mount_selector)
    entry = _Entry(neony, tree)
    entry.window = cast(Any, fake)
    app._entries.append(entry)
    neony._win = cast(Any, fake)
    app._registered.append(set())
    app._collect_handlers(neony, tree, 0, app._registered[0])
    app._arm_render_request(tree, 0)
    app._arm_eval_js_request(tree, 0)
    return neony


def _ops(fake: RecordingWindow) -> list[dict]:
    return [op for patch in fake.patches for op in patch["ops"]]


def _find_managed(el: DOMElement) -> DOMElement | None:
    if el._managed_content:
        return el
    for child in el.container:
        if isinstance(child, DOMElement):
            found = _find_managed(child)
            if found is not None:
                return found
    return None


# ── DOMElement._append_text ───────────────────────────────────────


class TestDOMAppendText:
    def test_append_accumulates_and_marks_structural(self):
        el = Span(container=["abc"])
        el._append_text("def")
        assert el.container == ["abc", "def"]
        assert el._dirty is True
        assert el._dirty_type & DOMElement._DIRTY_STRUCTURAL

    def test_append_after_plain_assignment_still_marks(self):
        el = Span()
        el.container = ["abc"]  # replaces the _Children wrapper
        el._append_text("def")
        assert el._dirty is True

    def test_append_rejects_element_children(self):
        el = Div(container=[Span()])
        with pytest.raises(ValueError, match="text-only"):
            el._append_text("no")

    def test_append_rejects_void(self):
        with pytest.raises(TypeError, match="Void"):
            Br()._append_text("no")


# ── Text component ────────────────────────────────────────────────


class TestTextStreaming:
    def test_append_text_accumulates(self):
        t = Text("Hello")
        t.append_text(", ").append_text("world")
        assert t.text == "Hello, world"

    def test_append_text_from_reactive_switches_to_imperative(self):
        sig = Signal("base")
        t = Text(sig)
        t.append_text("+more")
        assert t.text == "base+more"
        sig.set("changed")
        # The binding is disposed — the imperative text stands.
        assert t.text == "base+more"

    def test_setter_disposes_stale_binding(self):
        sig = Signal("first")
        t = Text(sig)
        t.text = "second"
        sig.set("changed")
        assert t.text == "second"

    def test_appends_render_as_one_append_patch(self):
        async def scenario():
            app = NeonApplication(Config(auto_render=True))
            fake = RecordingWindow()
            t = Text("hello")
            _setup(app, t.build(), fake)

            await app.render()
            fake.patches.clear()

            t.append_text(" world")
            t.append_text("!")
            await asyncio.sleep(0.01)

            ops = _ops(fake)
            assert [op["op"] for op in ops] == ["append_text"]
            assert ops[0]["text"] == " world!"

        asyncio.run(scenario())

    def test_diverged_write_renders_set_text(self):
        async def scenario():
            app = NeonApplication(Config(auto_render=True))
            fake = RecordingWindow()
            t = Text("hello")
            _setup(app, t.build(), fake)

            await app.render()
            fake.patches.clear()

            t.text = "goodbye"
            await asyncio.sleep(0.01)

            ops = _ops(fake)
            assert [op["op"] for op in ops] == ["set_text"]
            assert ops[0]["text"] == "goodbye"

        asyncio.run(scenario())

    def test_bound_signal_growth_renders_append_patch(self):
        async def scenario():
            app = NeonApplication(Config(auto_render=True))
            fake = RecordingWindow()
            sig = Signal("abc")
            t = Text(sig)
            _setup(app, t.build(), fake)

            await app.render()
            fake.patches.clear()

            sig.update(lambda s: s + "def")
            await asyncio.sleep(0.01)

            ops = _ops(fake)
            assert [op["op"] for op in ops] == ["append_text"]
            assert ops[0]["text"] == "def"

        asyncio.run(scenario())


# ── stream() ──────────────────────────────────────────────────────


class TestStream:
    def test_sync_iterable_stream(self):
        async def scenario():
            t = Text("")
            await t.stream(["a", "b", "c"])
            assert t.text == "abc"

        asyncio.run(scenario())

    def test_async_iterator_stream(self):
        async def tokens():
            for chunk in ("x", "y", "z"):
                yield chunk

        async def scenario():
            t = Text("")
            await t.stream(tokens())
            assert t.text == "xyz"

        asyncio.run(scenario())

    def test_burst_coalesces_into_few_appends(self):
        async def scenario():
            app = NeonApplication(Config(auto_render=True))
            fake = RecordingWindow()
            t = Text("")
            _setup(app, t.build(), fake)
            await app.render()
            fake.patches.clear()

            # Thirty chunks in one burst: they coalesce into few appends
            # (frame-batched by the pump, then merged again by the app's
            # per-turn render coalescing) — never one patch per token.
            await t.stream([str(i) for i in range(30)])
            await asyncio.sleep(0.02)  # let scheduled renders commit
            ops = _ops(fake)
            assert len(ops) < 10
            assert all(op["op"] == "append_text" for op in ops)
            assert "".join(op["text"] for op in ops) == "".join(str(i) for i in range(30))

        asyncio.run(scenario())

    def test_isolated_tokens_flush_immediately(self):
        async def tokens():
            yield "a"
            await asyncio.sleep(0.05)
            yield "b"

        async def scenario():
            app = NeonApplication(Config(auto_render=True))
            fake = RecordingWindow()
            t = Text("")
            _setup(app, t.build(), fake)
            await app.render()
            fake.patches.clear()

            await t.stream(tokens())
            await asyncio.sleep(0.02)  # let scheduled renders commit
            assert t.text == "ab"
            assert [op["op"] for op in _ops(fake)] == ["append_text", "append_text"]
            assert [op["text"] for op in _ops(fake)] == ["a", "b"]

        asyncio.run(scenario())

    def test_concurrent_stream_raises(self):
        async def slow():
            yield "a"
            await asyncio.sleep(0.05)
            yield "b"

        async def scenario():
            t = Text("")
            task = t.stream(slow())
            await asyncio.sleep(0)
            with pytest.raises(RuntimeError, match="already running"):
                t.stream(["x"])
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task

        asyncio.run(scenario())

    def test_cancel_keeps_consumed_text(self):
        async def slow():
            yield "kept"
            await asyncio.sleep(10)
            yield "never"

        async def scenario():
            t = Text("")
            task = t.stream(slow())
            await asyncio.sleep(0.01)
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
            assert t.text == "kept"

        asyncio.run(scenario())

    def test_stop_stream_without_stream_is_false(self):
        assert Text("").stop_stream() is False

    def test_stream_sends_begin_and_end_markers(self):
        async def scenario():
            app = NeonApplication(Config(auto_render=True))
            fake = RecordingWindow()
            t = Text("")
            _setup(app, t.build(), fake)
            key = json.dumps(t._root.key)

            await t.stream(["a", "b"])
            await asyncio.sleep(0.02)

            begins = [s for s in fake.scripts if "window.neony.stream.begin" in s]
            ends = [s for s in fake.scripts if "window.neony.stream.end" in s]
            assert begins == [f"window.neony.stream.begin({key}, false)"]
            assert ends == [f"window.neony.stream.end({key})"]

        asyncio.run(scenario())

    def test_bubble_stream_requests_glow(self):
        async def scenario():
            app = NeonApplication(Config(auto_render=True))
            fake = RecordingWindow()
            b = MessageBubble("")
            _setup(app, b.build(), fake)
            key = json.dumps(b._bubble.key)

            await b.stream(["hi"])
            await asyncio.sleep(0.02)

            begins = [s for s in fake.scripts if "window.neony.stream.begin" in s]
            assert begins == [f"window.neony.stream.begin({key}, true)"]

        asyncio.run(scenario())

    def test_cancelled_stream_still_sends_end(self):
        async def slow():
            yield "a"
            await asyncio.sleep(10)

        async def scenario():
            app = NeonApplication(Config(auto_render=True))
            fake = RecordingWindow()
            t = Text("")
            _setup(app, t.build(), fake)
            key = json.dumps(t._root.key)

            task = t.stream(slow())
            await asyncio.sleep(0.01)
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
            await asyncio.sleep(0.02)

            ends = [s for s in fake.scripts if "window.neony.stream.end" in s]
            assert ends == [f"window.neony.stream.end({key})"]

        asyncio.run(scenario())

    def test_stop_stream_cancels(self):
        async def slow():
            yield "kept"
            await asyncio.sleep(10)
            yield "never"

        async def scenario():
            t = Text("")
            t.stream(slow())
            await asyncio.sleep(0.01)
            assert t.stop_stream() is True
            await asyncio.sleep(0.01)
            assert t.text == "kept"

        asyncio.run(scenario())


# ── chat bubbles ──────────────────────────────────────────────────


class TestChatStreaming:
    def test_bubble_append(self):
        b = MessageBubble("Hello")
        b.append_text(" there")
        assert b.text == "Hello there"

    def test_bubble_with_custom_content_rejects_append(self):
        b = MessageBubble(content=Text("custom"))
        with pytest.raises(ValueError, match="custom content"):
            b.append_text("no")

    def test_bubble_with_custom_content_rejects_stream(self):
        b = MessageBubble(content=Text("custom"))
        with pytest.raises(ValueError, match="custom content"):
            b.stream(["no"])

    def test_notice_append(self):
        n = NoticeBubble("a")
        n.append_text("b")
        assert n.text == "ab"

    def test_bubble_appends_render_append_patch(self):
        async def scenario():
            app = NeonApplication(Config(auto_render=True))
            fake = RecordingWindow()
            b = MessageBubble("hi")
            _setup(app, b.build(), fake)

            await app.render()
            fake.patches.clear()

            b.append_text("!")
            await asyncio.sleep(0.01)

            assert [op["op"] for op in _ops(fake)] == ["append_text"]

        asyncio.run(scenario())


# ── Markdown ──────────────────────────────────────────────────────


class TestMarkdown:
    def test_root_is_managed_and_marked(self):
        md = Markdown("# Hi")
        root = md.build()
        assert root._managed_content is True
        assert root.args["data-neony-markdown"] == "true"

    def test_first_snapshot_carries_source(self):
        md = Markdown("# Hi\n\n**bold**")
        node = md.build().to_node()
        assert node.text == "# Hi\n\n**bold**"

    def test_provider_tracks_appends(self):
        md = Markdown("# Hi")
        root = md.build()
        assert root.to_node().text == "# Hi"
        md.append_text(" there")
        provider = root._managed_source
        assert provider is not None
        assert provider() == "# Hi there"

    def test_managed_snapshot_never_changes(self):
        md = Markdown("# Hi")
        root = md.build()
        frozen = root.to_node()
        md.append_text(" there")
        # Live content is JS-owned — a re-serialization (with the cached
        # snapshot in place) returns the frozen node unchanged.
        assert root.to_node(snapshot_cache={root.key: frozen}) is frozen

    def test_push_command_carries_full_source(self):
        async def scenario():
            app = NeonApplication(Config(auto_render=True))
            fake = RecordingWindow()
            md = Markdown("")
            _setup(app, md.build(), fake)

            md.append_text("**stream**")
            await asyncio.sleep(0.01)

            commands = [s for s in fake.scripts if "window.neony.markdown.set" in s]
            assert len(commands) == 1
            expected_arg = json.dumps("**stream**")
            assert f"window.neony.markdown.set({json.dumps(md.root_element.key)}, {expected_arg})" in commands[0]

        asyncio.run(scenario())

    def test_reactive_source_pushes_on_change(self):
        async def scenario():
            sig = Signal("# start")
            app = NeonApplication(Config(auto_render=True))
            fake = RecordingWindow()
            md = Markdown(sig)
            _setup(app, md.build(), fake)
            sig.set("# changed")
            await asyncio.sleep(0.01)
            commands = [s for s in fake.scripts if "window.neony.markdown.set" in s]
            assert commands, "expected a push command"
            assert json.dumps("# changed") in commands[0]

        asyncio.run(scenario())

    def test_markdown_bubble_proxies_streaming(self):
        b = MessageBubble(markdown=True)
        b.append_text("# Title\n\n")
        b.append_text("- item")
        assert b.text == "# Title\n\n- item"
        host = _find_managed(b.build())
        assert host is not None
        assert host.args["data-neony-markdown"] == "true"

    def test_plain_bubble_has_no_managed_host(self):
        b = MessageBubble("plain")
        assert _find_managed(b.build()) is None


# ── Markdown stylesheet ───────────────────────────────────────────


class TestMarkdownCss:
    """The markdown stylesheet must be fully theme-token driven."""

    def test_no_literal_colors(self):
        # Every colour rides a --color-* token — the stylesheet carries no
        # hex or rgba literals at all, so themes fully own the palette.
        assert re.findall(r"#[0-9a-fA-F]{3,8}\b", MARKDOWN_CSS) == []
        assert "rgba(" not in MARKDOWN_CSS

    def test_fenced_code_gets_a_pure_uniform_well(self):
        pre_block = MARKDOWN_CSS[MARKDOWN_CSS.index("[data-neony-markdown] pre {") :]
        pre_block = pre_block[: pre_block.index("}")]
        # Pure page background: one clean dark per dark preset, one clean
        # light per light preset — no theme hue blended in.  Hosts re-point
        # the whole value via --md-well-bg.
        assert "background-color: var(--md-well-bg);" in pre_block
        assert "color-mix" not in pre_block
        assert "--md-well-bg: var(--color-bg);" in MARKDOWN_CSS
        assert "border: 1px solid var(--md-line)" in pre_block
        # The code element inside stays transparent so the well shows.
        assert "background: transparent" in MARKDOWN_CSS
        # Table bands are host-tunable via --md-*.
        assert "--md-th-chip: var(--md-chip);" in MARKDOWN_CSS
        assert "--md-zebra: var(--md-chip);" in MARKDOWN_CSS
        assert "background: var(--md-th-chip)" in MARKDOWN_CSS
        assert "background: var(--md-zebra)" in MARKDOWN_CSS

    def test_well_text_stays_page_text(self):
        # Code ink never follows the host bubble's text color — the well
        # keeps page-readable text on every fill.
        pre_code = MARKDOWN_CSS[MARKDOWN_CSS.index("[data-neony-markdown] pre code {") :]
        pre_code = pre_code[: pre_code.index("}")]
        assert "color: var(--color-text-primary)" in pre_code
        inline = MARKDOWN_CSS[MARKDOWN_CSS.index("[data-neony-markdown] code {") :]
        inline = inline[: inline.index("}")]
        assert "color: var(--color-text-primary)" in inline

    def test_highlight_palette_is_token_driven(self):
        palette = MARKDOWN_CSS[MARKDOWN_CSS.index(".hljs-comment") : MARKDOWN_CSS.index("blockquote")]
        assert ".hljs-keyword" in palette
        assert "var(--color-accent)" in palette
        assert ".hljs-string" in palette
        assert "var(--color-success)" in palette
        assert ".hljs-number" in palette
        assert "var(--color-danger)" in palette
        assert "var(--color-text-secondary)" in palette

    def test_structural_theming(self):
        # Headings carry a token border, tables zebra-stripe with a token.
        assert "border-bottom: 1px solid var(--md-line)" in MARKDOWN_CSS
        assert "tbody tr:nth-child(even)" in MARKDOWN_CSS

    def test_md_custom_property_indirection(self):
        # Every content colour goes through --md-* custom properties that
        # default to theme tokens — hosts on colored surfaces re-point
        # them instead of fighting the tokens.
        for prop in ("--md-text", "--md-muted", "--md-link", "--md-chip", "--md-line"):
            assert f"{prop}: var(--color-" in MARKDOWN_CSS
        assert "color: var(--md-text)" in MARKDOWN_CSS

    def test_accent_bubble_repoints_md_vars(self):
        b = MessageBubble(markdown=True, from_me=True)
        host = _find_managed(b.build())
        assert host is not None
        style = host.args.get("style")
        assert style is not None
        # No literal colours — tokens and token mixes only.
        assert "white" not in style
        assert "rgba(" not in style
        # Text follows on_accent; the code well is handed wholesale to
        # accent_secondary; links, rules and table bands ride the same
        # secondary hue.
        assert "--md-text: var(--color-on-accent)" in style
        assert "--md-muted: color-mix(in srgb, var(--color-on-accent) 72%, transparent)" in style
        # Inline code chips join the well on the secondary hue.
        assert "--md-chip: var(--color-accent-secondary)" in style
        assert "--md-link: var(--color-accent-secondary)" in style
        assert "--md-line: color-mix(in srgb, var(--color-accent-secondary) 60%, transparent)" in style
        assert "--md-well-bg: var(--color-accent-secondary)" in style
        assert "--md-th-chip: color-mix(in srgb, var(--color-accent-secondary) 45%, transparent)" in style
        assert "--md-zebra: color-mix(in srgb, var(--color-accent-secondary) 22%, transparent)" in style
        # Accent-family highlight tokens go neutral on the same-hue well.
        assert "--md-hi-keyword: var(--color-text-primary)" in style
        assert "--md-hi-dim: var(--color-text-primary)" in style
        # A left bubble keeps the default (token) values.
        left = _find_managed(MessageBubble(markdown=True).build())
        assert left is not None
        assert "style" not in left.args

    def test_streaming_effect_rules(self):
        from neony.application._helpers import _BUILTIN_KEYFRAMES, STREAMING_CSS

        names = [kf.name for kf in _BUILTIN_KEYFRAMES]
        for name in ("neony-caret-blink", "neony-stream-chunk-in", "neony-stream-glow"):
            assert name in names
        assert "[data-neony-streaming]::after" in STREAMING_CSS
        assert ".neony-stream-chunk" in STREAMING_CSS
        assert "[data-neony-stream-glow]" in STREAMING_CSS
        # Token-pure colours only.
        assert re.findall(r"#[0-9a-fA-F]{3,8}\b", STREAMING_CSS) == []
        assert "rgba(" not in STREAMING_CSS
        assert "0.2s" in STREAMING_CSS

    def test_bubble_text_color_is_a_token(self):
        from neony.application.elements.chat import _BUBBLE_ME
        from neony.application.theme import stub

        assert _BUBBLE_ME.color == stub.on_accent

    def test_every_theme_derives_accent_secondary_from_accent(self):
        from neony.application.theme import Theme, secondary_accent, stub

        assert stub.accent_secondary == Color(var="--color-accent-secondary")
        for mode in Theme.modes():
            theme = Theme.get(mode)
            # on-accent text is white across the built-ins, and the
            # secondary accent is the accent hue shifted toward the page
            # background.
            assert theme.on_accent == Color(hex="#ffffff"), mode
            expected = secondary_accent(theme.accent, theme.bg)
            assert theme.accent_secondary == expected, mode
            assert f"--color-accent-secondary: {theme.accent_secondary};" in theme.to_css()
