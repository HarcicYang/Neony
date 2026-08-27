"""Video / Audio 组件测试 — 构建结构、源所有权路由、响应式状态与命令."""

from __future__ import annotations

import asyncio
import json

import pytest

from neony.application.elements.media import Audio, Video
from neony.dom import Audio as DomAudio
from neony.dom import Signal, Styles
from neony.dom import Video as DomVideo
from neony.dom.base import DOMElement


def _inner(component: Video | Audio) -> DOMElement:
    inner = component.build().container[0]
    assert isinstance(inner, DOMElement)
    return inner


def _video_inner(component: Video) -> DOMElement:
    return _inner(component)


def _audio_inner(component: Audio) -> DOMElement:
    return _inner(component)


class TestStructure:
    def test_protocol_video_hides_src_and_emits_contract(self) -> None:
        component = Video("neony://local/clip.mp4", poster="https://x/p.jpg", width=480)
        root = component.build()
        assert isinstance(root, DOMElement)
        media = root.container[0]
        assert isinstance(media, DomVideo)
        inner = media

        assert inner.src is None  # neony:// 永不落 src 属性
        assert inner.args["data-neony-media-src"] == "neony://local/clip.mp4"
        assert "timeupdate" in inner.args["data-neony-direct-events"]
        assert inner.poster == "https://x/p.jpg"
        # 原生控件关闭 + transport 存在 [frame: media + transport]
        assert not getattr(inner, "controls", None)
        assert len(root.container) == 2

    def test_native_video_uses_plain_src(self) -> None:
        component = Video("https://example.com/clip.mp4")
        media = _video_inner(component)
        assert isinstance(media, DomVideo)
        inner = media

        assert inner.src == "https://example.com/clip.mp4"
        assert "data-neony-media-src" not in inner.args

    def test_audio_mounts_inner_element_and_transport(self) -> None:
        component = Audio("neony://local/song.mp3")
        root = component.build()
        assert isinstance(root, DOMElement)
        transport = root.container[1]
        assert isinstance(transport, DOMElement)

        assert type(root.container[0]).__name__ == "Audio"
        assert len(transport.container) >= 5  # play/time/seek/duration/mute/volume

    def test_audio_public_media_styles(self) -> None:
        component = Audio(
            "neony://local/song.mp3",
            media_styles=Styles(display="block", width="100%", align_self="stretch"),
        )
        media = _audio_inner(component)
        assert isinstance(media, DomAudio)
        assert media.styles.display == "block"
        assert media.styles.width == "100%"
        assert media.styles.align_self == "stretch"

    def test_transport_buttons_are_compact_icon_targets(self) -> None:
        component = Audio("https://example.com/song.mp3")
        component.build()

        for button in (component._play_button, component._mute_button):
            assert button._root.styles.width == "32px"
            assert button._root.styles.height == "28px"
            assert button._root.styles.padding == "0"
            assert button._icon_span is not None
            assert button._icon_span.bubble_events is True
            assert button._root.to_node().styles["color"] == "var(--color-text-primary)"
            assert button._root.to_node().attrs["data-neony-event-scope"] == ""


class TestSourceSwitching:
    def test_bind_src_switches_between_contract_and_native(self) -> None:
        signal = Signal("neony://local/a.mp4")
        component = Audio(signal())
        component.bind_src(signal)
        root = component.build()
        assert isinstance(root, DOMElement)
        media = root.container[0]
        assert isinstance(media, DomAudio)
        inner = media
        assert inner.args.get("data-neony-media-src") == "neony://local/a.mp4"

        signal.set("https://example.com/b.mp3")
        loop = asyncio.new_event_loop()
        loop.run_until_complete(asyncio.sleep(0))
        loop.close()
        assert inner.args.get("data-neony-media-src") is None
        assert inner.src == "https://example.com/b.mp3"

        signal.set("neony://local/c.mp4")
        loop = asyncio.new_event_loop()
        loop.run_until_complete(asyncio.sleep(0))
        loop.close()
        assert inner.args.get("data-neony-media-src") == "neony://local/c.mp4"
        assert inner.src is None


class TestStateSync:
    @pytest.mark.parametrize(
        ("event_type", "field", "expected"),
        [
            ("play", "playing", True),
            ("pause", "playing", False),
            ("ended", "playing", False),
        ],
    )
    def test_playback_state_events(self, event_type: str, field: str, expected: bool) -> None:
        component = Audio("neony://local/song.mp3")

        async def fire() -> None:
            await component._on_event(
                event_type,
                __import__("neony.dom", fromlist=["DomEvent"]).DomEvent(key="m", type=event_type),
            )

        asyncio.run(fire())
        assert getattr(component, field) is expected

    def test_timeupdate_updates_position_and_slider(self) -> None:
        component = Audio("neony://local/song.mp3")
        dom_event = __import__("neony.dom", fromlist=["DomEvent"]).DomEvent(
            key="m", type="loadedmetadata", media_duration=200.0
        )

        async def fire_loaded() -> None:
            await component._on_event("loadedmetadata", dom_event)

        asyncio.run(fire_loaded())

        async def fire_time() -> None:
            await component._on_event(
                "timeupdate",
                __import__("neony.dom", fromlist=["DomEvent"]).DomEvent(key="m", type="timeupdate", media_time=50.0),
            )

        asyncio.run(fire_time())

        assert component.position == pytest.approx(50.0)
        assert component.duration == pytest.approx(200.0)
        assert component._position_slider.value == pytest.approx(25.0)

    def test_scrubbing_suppresses_slider_sync(self) -> None:
        component = Audio("neony://local/song.mp3")

        async def seed() -> None:
            await component._on_event(
                "loadedmetadata",
                __import__("neony.dom", fromlist=["DomEvent"]).DomEvent(
                    key="m", type="loadedmetadata", media_duration=100.0
                ),
            )

        asyncio.run(seed())
        component._scrubbing = True

        async def fire_time() -> None:
            await component._on_event(
                "timeupdate",
                __import__("neony.dom", fromlist=["DomEvent"]).DomEvent(key="m", type="timeupdate", media_time=90.0),
            )

        asyncio.run(fire_time())
        # 时间信号照常更新, 但滑块不被拖动中的写入覆盖
        assert component.position == pytest.approx(90.0)
        assert component._position_slider.value == pytest.approx(0.0)


class TestLoadingPhase:
    """水合阶段回环 — JS 经 media_loading 合成事件驱动加载条。"""

    def test_media_loading_event_flips_signal(self) -> None:
        component = Audio("neony://local/song.mp3")
        inner = _audio_inner(component)
        assert "media_loading" in inner._handlers  # 已注册 [无 DOM 监听]
        assert component._loading() is False

        handler = inner._handlers["media_loading"][0]

        async def fire(active: bool) -> None:
            await handler(
                __import__("neony.dom", fromlist=["DomEvent"]).DomEvent(key="m", type="media_loading", value=active)
            )

        asyncio.run(fire(True))
        assert component._loading() is True
        asyncio.run(fire(False))
        assert component._loading() is False

    def test_loading_overlay_and_slider_visibility(self) -> None:
        from neony.application.elements.progress import Progress

        component = Audio("neony://local/song.mp3")
        inner = _audio_inner(component)
        assert isinstance(component._loading_bar, Progress)
        handler = inner._handlers["media_loading"][0]

        async def fire(active: bool) -> None:
            await handler(
                __import__("neony.dom", fromlist=["DomEvent"]).DomEvent(key="m", type="media_loading", value=active)
            )

        def toggle_and_check(active: bool) -> tuple[str | None, str | None]:
            asyncio.run(fire(active))
            loop = asyncio.new_event_loop()
            try:
                loop.run_until_complete(asyncio.sleep(0))  # 放行 bind_visible effect
            finally:
                loop.close()
            slider_display = component._position_slider._root.to_node().styles.get("display")
            overlay_display = component._loading_overlay.to_node().styles.get("display")
            return slider_display, overlay_display

        slider_display, overlay_display = toggle_and_check(True)
        assert slider_display == "none"  # 水合中: 滑块让位
        assert overlay_display != "none"  # 加载条占据进度槽位

        slider_display, overlay_display = toggle_and_check(False)
        assert slider_display != "none"
        assert overlay_display == "none"


class TestSourceChangeResetsPlayback:
    """换源即失效 — 旧资源的播放事实必须清零, 否则 toggle 会把
    "正在播" 当真而永远暂停一个没在播的新元素."""

    def _seed_playing_state(self, component: Audio) -> None:
        async def seed() -> None:
            await component._on_event(
                "play", __import__("neony.dom", fromlist=["DomEvent"]).DomEvent(key="m", type="play")
            )
            await component._on_event(
                "loadedmetadata",
                __import__("neony.dom", fromlist=["DomEvent"]).DomEvent(
                    key="m", type="loadedmetadata", media_duration=120.0
                ),
            )
            await component._on_event(
                "timeupdate",
                __import__("neony.dom", fromlist=["DomEvent"]).DomEvent(key="m", type="timeupdate", media_time=42.0),
            )

        asyncio.run(seed())

    def test_src_setter_resets_playback_state(self) -> None:
        signal = Signal("neony://local/a.mp4")
        component = Audio(signal())
        self._seed_playing_state(component)
        assert component.playing and component.position > 0

        component.src = "neony://local/b.mp4"
        assert not component.playing
        assert component.position == 0.0
        assert component.duration == 0.0

    def test_bind_src_signal_change_resets_slider(self) -> None:
        import math

        signal = Signal("neony://local/a.mp4")
        component = Audio(signal())
        component.bind_src(signal)
        inner = _audio_inner(component)
        self._seed_playing_state(component)

        async def drive() -> None:
            await component._on_event(
                "timeupdate",
                __import__("neony.dom", fromlist=["DomEvent"]).DomEvent(key="m", type="timeupdate", media_time=60.0),
            )

        asyncio.run(drive())  # 滑块走到 50%
        assert not math.isclose(component._position_slider.value, 0.0)

        signal.set("neony://local/b.mp3")
        loop = asyncio.new_event_loop()
        loop.run_until_complete(asyncio.sleep(0))
        loop.close()
        assert not component.playing
        assert component._position_slider.value == 0.0
        assert inner.args.get("data-neony-media-src") == "neony://local/b.mp3"


class TestDirectEventBinding:
    """直连事件必须绑在内部媒体元素上 — 它们不冒泡, frame 根永远看不到."""

    def test_inner_element_carries_state_handlers(self) -> None:
        component = Audio("neony://local/song.mp3")
        inner = _audio_inner(component)
        for event_type in ("timeupdate", "play", "pause", "ended", "volumechange", "loadedmetadata"):
            assert event_type in inner._handlers, f"{event_type} 未绑定到媒体元素"

    def test_firing_inner_handler_syncs_state_and_user_callback(self) -> None:
        component = Audio("neony://local/song.mp3")
        inner = _audio_inner(component)
        seen: list[str] = []
        component.on_timeupdate(lambda _event: seen.append("tick"))

        handler = inner._handlers["timeupdate"][0]
        dom_event = __import__("neony.dom", fromlist=["DomEvent"]).DomEvent(key="m", type="timeupdate", media_time=7.5)
        asyncio.run(handler(dom_event))

        assert component.position == pytest.approx(7.5)
        assert seen == ["tick"]  # 恰好一次 —— 无 root 双重派发

    def test_user_callback_does_not_lazy_wire_the_root(self) -> None:
        component = Video("neony://local/clip.mp4")
        component.on_play(lambda _event: None)
        # play 在 _bound_events 里 → 不应再往 frame 根上挂第二个 dispatcher
        assert "play" not in component._root._handlers


class TestCommands:
    def test_commands_target_media_key_via_call_js(self, monkeypatch: pytest.MonkeyPatch) -> None:
        captured: list[str] = []

        async def fake_call_js(script: str) -> None:
            captured.append(script)

        component = Video("neony://local/clip.mp4")
        monkeypatch.setattr(component, "_call_js", fake_call_js)

        async def run() -> None:
            await component.play()
            await component.pause()
            await component.seek(12.5)
            await component.set_muted(True)
            await component.set_volume(0.3)

        asyncio.run(run())

        key = json.dumps(component._media.key)
        assert captured[0] == f"window.neony.mediaPlay({key})"
        assert captured[1] == f"window.neony.mediaPause({key})"
        assert captured[2] == f"window.neony.mediaSeek({key}, 12.5)"
        assert captured[3] == f"window.neony.mediaSetMuted({key}, true)"
        assert captured[4] == f"window.neony.mediaSetVolume({key}, 0.3)"

    def test_user_callbacks_dispatch(self) -> None:
        seen: list[str] = []
        component = Video("neony://local/clip.mp4")
        component.on_play(lambda _event: seen.append("play"))
        component.on_error(lambda _event: seen.append("error"))

        async def run() -> None:
            await component._on_event(
                "play", __import__("neony.dom", fromlist=["DomEvent"]).DomEvent(key="m", type="play")
            )
            await component._on_event(
                "error",
                __import__("neony.dom", fromlist=["DomEvent"]).DomEvent(key="m", type="error", media_error=4),
            )

        asyncio.run(run())
        assert seen == ["play", "error"]
