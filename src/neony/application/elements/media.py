"""Video / Audio components — fully managed, themed media players.

Ownership model: the component is the *only* decision-maker for a media
source.  A ``neony://`` source never lands in the DOM ``src`` attribute
(WebKitGTK's media pipeline cannot resolve custom schemes, and a
mid-flight src swap leaves it stuck on the interrupted load forever).
Instead, the component emits the ``data-neony-media-src`` contract
attribute; the JS runtime hydrates that contract (fetch → Blob URL →
clean ``src`` assignment + ``load()``) and wires the non-bubbling media
events (``data-neony-direct-events``).  Non-protocol sources (https,
data) take the browser's native path.

Native controls are hidden — playback is driven by the themed transport
row (play/pause, position slider, time labels, mute, volume) built from
regular Neony components and updated reactively from media events.
"""

from __future__ import annotations

import asyncio
import json
from typing import Literal, Self

from neony.application.elements.button import Button
from neony.application.elements.icon import Icon
from neony.application.elements.progress import Progress
from neony.application.elements.slider import Slider
from neony.application.elements.text import Text
from neony.application.media_compat import ensure_playable_source
from neony.application.theme import stub
from neony.dom import Audio as DomAudio
from neony.dom import Div, Signal, Styles, Transform
from neony.dom import Video as DomVideo
from neony.dom.base import DOMElement
from neony.dom.reactive import Computed, Effect, effect

from .base import Component

_Preload = Literal["none", "metadata", "auto"]

#: Non-bubbling media events wired directly onto the inner element.
_DIRECT_EVENTS = (
    "timeupdate",
    "loadedmetadata",
    "durationchange",
    "play",
    "pause",
    "ended",
    "volumechange",
    "seeked",
    "waiting",
    "error",
)

_PLAY_ICON = Icon._font("play_arrow")
_PAUSE_ICON = Icon._font("pause")
_VOLUME_UP_ICON = Icon._font("volume_up")
_VOLUME_OFF_ICON = Icon._font("volume_off")
_MEDIA_BUTTON = Styles(
    display="flex",
    align_items="center",
    justify_content="center",
    width="32px",
    height="28px",
    padding="0",
    border="none",
    border_radius="8px",
    background_color=stub.surface,
    # reset_styles() replaces Button's variant palette; keep an explicit
    # themed foreground so the inherited-font icons follow dark/light.
    color=stub.text_primary,
)


def _fmt_time(seconds: float | None) -> str:
    """``75.4`` → ``"1:15"``; hours only when needed."""
    if seconds is None or seconds != seconds or seconds < 0:  # None / NaN / negative
        return "0:00"
    total = int(seconds)
    hours, rem = divmod(total, 3600)
    minutes, secs = divmod(rem, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def _dim(value: str | int | None) -> str | None:
    """Coerce a dimension argument — ints become ``"Npx"``."""
    if value is None:
        return None
    if isinstance(value, int):
        return f"{value}px"
    return value


def _mount(child: Component | DOMElement) -> DOMElement:
    """Materialize a component child for a raw DOM container."""
    return child.build() if isinstance(child, Component) else child


def _merge_styles(base: Styles, overrides: Styles) -> Styles:
    """Apply the overrides' explicitly-set fields while retaining nested values."""
    return base.model_copy(update={key: getattr(overrides, key) for key in overrides.model_fields_set})


class _MediaBase(Component):
    _media: DomVideo | DomAudio
    """Shared engine of the media components: source ownership, the
    hydration contract, direct-event state sync and the themed transport
    row.  Subclasses assemble the concrete layout."""

    #: All direct events are bound to the inner media element in
    #: ``__init__`` — they fire there and never bubble, so the base lazy
    #: ``_wire_root`` path could never see them.
    _bound_events = frozenset(_DIRECT_EVENTS)

    def __init__(
        self,
        src: str,
        *,
        autoplay: bool = False,
        loop: bool = False,
        muted: bool = False,
        preload: _Preload = "metadata",
    ) -> None:
        super().__init__()
        self._src = src
        self._preload: _Preload = preload

        # Reactive playback state — the single source of truth for the
        # transport UI.  Media events write; bindings read.
        self._playing = Signal(False)
        self._time_sig = Signal(0.0)
        self._duration_sig = Signal(0.0)
        self._is_muted = Signal(muted)
        self._volume_sig = Signal(1.0)
        # True while the runtime reads/hydrates the source (JS reports it
        # via the synthetic media_loading event).
        self._loading = Signal(False)
        # While the user drags the position slider, timeupdate writes are
        # suppressed so the thumb doesn't fight the pointer.
        self._scrubbing = False
        self._src_effect: Effect | None = None

    def _bind_direct_events(self) -> None:
        """Attach the state-sync dispatcher to the inner media element.

        Media events fire on the inner element and do not bubble; this is
        the only path by which playback state reaches Python.
        """
        for event_type in _DIRECT_EVENTS:
            self._bind(self._media, event_type)
        # Synthetic hydration-phase event: JS invokes it directly through
        # the bridge — no DOM listener exists, so record the handler
        # without touching data-neony-direct-events.
        self._media.on("media_loading", self._make_handler("media_loading"))

    # ---- source ownership ----

    @staticmethod
    def _is_protocol_src(src: str) -> bool:
        return src.startswith("neony://")

    def _schedule_source_resolution(self) -> None:
        """Resolve codec compatibility for *src*, then route the result
        through the right channel (hydration contract for ``neony://``,
        native attribute for everything else).

        A source change invalidates every playback fact about the old
        resource — reset the reactive state so transport UI and command
        handlers reflect the fresh (not-yet-playing) element."""
        requested = self._src
        self._playing.set(False)
        self._time_sig.set(0.0)
        self._duration_sig.set(0.0)
        self._scrubbing = False
        slider = getattr(self, "_position_slider", None)
        if slider is not None:
            slider.value = 0.0

        async def _resolve() -> None:
            resolved = await ensure_playable_source(requested)
            # Skip if the user changed src again while we were working.
            if self._src == requested:
                self._apply_resolved(resolved)

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # No event loop (pure-sync build phase) — apply directly;
            # transcode fallback simply cannot run here.
            self._apply_resolved(requested)
            return
        task = loop.create_task(_resolve())
        # Reuse the JS-task set to hold a strong reference.
        self._js_tasks.add(task)
        task.add_done_callback(self._js_tasks.discard)

    def _apply_resolved(self, resolved: str) -> None:
        """Route *resolved* through the right channel."""
        if self._is_protocol_src(resolved):
            self._media._set_attr("data-neony-media-src", resolved)
            self._media.src = None
        else:
            self._media.src = resolved
            self._media._set_attr("data-neony-media-src", None)

    @property
    def src(self) -> str:
        return self._src

    @src.setter
    def src(self, value: str) -> None:
        self._src = value
        self._schedule_source_resolution()

    def bind_src(self, signal: Signal[str]) -> Self:
        """Keep ``src`` in lockstep with *signal* (one-way)."""
        self.unbind_src()

        def write() -> None:
            self.src = signal()

        self._src_effect = effect(write)
        return self

    def unbind_src(self) -> Self:
        if self._src_effect is not None:
            self._src_effect.dispose()
            self._src_effect = None
        return self

    def unbind(self) -> Self:
        self.unbind_src()
        return super().unbind()

    # ---- transport commands ----
    #
    # Same channel as ScrollArea: private window.neony.* commands through
    # the tree's eval hook.  No-ops before the app arms the hook.

    def _media_key(self) -> str:
        return json.dumps(self._media.key)

    async def _issue(self, script: str) -> None:
        """Fire a media command through the eval hook (no-op pre-mount)."""
        coro = self._call_js(script)
        if coro is not None:
            await coro

    async def play(self) -> None:
        await self._issue(f"window.neony.mediaPlay({self._media_key()})")

    async def pause(self) -> None:
        await self._issue(f"window.neony.mediaPause({self._media_key()})")

    async def seek(self, seconds: float) -> None:
        await self._issue(f"window.neony.mediaSeek({self._media_key()}, {seconds!r})")

    async def set_muted(self, muted: bool) -> None:
        await self._issue(f"window.neony.mediaSetMuted({self._media_key()}, {json.dumps(muted)})")

    async def toggle_muted(self) -> None:
        await self.set_muted(not self._is_muted())

    async def set_volume(self, volume: float) -> None:
        await self._issue(f"window.neony.mediaSetVolume({self._media_key()}, {volume!r})")

    # ---- reactive reads ----

    @property
    def playing(self) -> bool:
        return self._playing()

    @property
    def position(self) -> float:
        return self._time_sig()

    @property
    def duration(self) -> float:
        return self._duration_sig()

    @property
    def muted(self) -> bool:
        return self._is_muted()

    @property
    def volume(self) -> float:
        return self._volume_sig()

    # ---- event API ----

    def on_play(self, fn) -> Self:
        return self.on("play", fn)

    def on_pause(self, fn) -> Self:
        return self.on("pause", fn)

    def on_ended(self, fn) -> Self:
        return self.on("ended", fn)

    def on_timeupdate(self, fn) -> Self:
        return self.on("timeupdate", fn)

    def on_error(self, fn) -> Self:
        return self.on("error", fn)

    async def _on_event(self, event_type: str, event) -> None:
        if event_type == "play":
            self._playing.set(True)
        elif event_type in ("pause", "ended"):
            self._playing.set(False)
        elif event_type == "timeupdate" and event.media_time is not None:
            self._time_sig.set(event.media_time)
            self._sync_position()
        elif event_type in ("loadedmetadata", "durationchange") and event.media_duration:
            self._duration_sig.set(event.media_duration)
        elif event_type == "volumechange":
            if event.media_muted is not None:
                self._is_muted.set(event.media_muted)
            if event.media_volume is not None:
                self._volume_sig.set(event.media_volume)
        elif event_type == "media_loading":
            self._loading.set(bool(event.value))
        await self._dispatch(event_type, event)

    def _sync_position(self) -> None:
        """Reflect playback time onto the position slider (percent-based,
        so an unknown duration needs no special casing)."""
        if self._scrubbing:
            return
        duration = self._duration_sig()
        if duration > 0:
            self._position_slider.value = min(100.0, self._time_sig() / duration * 100.0)

    # ---- transport construction ----

    def _transport_row(self) -> Div:
        """Themed control strip shared by both components."""
        self._play_button = Button("", variant="ghost", icon=_PLAY_ICON)
        self._play_button.reset_styles(_MEDIA_BUTTON)
        self._play_button.on_click(lambda _event: self.pause() if self._playing() else self.play())
        effect(lambda: setattr(self._play_button, "icon", _PAUSE_ICON if self._playing() else _PLAY_ICON))

        self._time_label = Text("0:00", role="secondary")
        self._time_label.bind_text(self._time_sig, fmt=_fmt_time)

        self._position_slider = Slider("", min=0.0, max=100.0, step="any", value=0.0)
        self._position_slider.on_input(self._on_scrub_input)
        self._position_slider.on_change(self._on_scrub_change)

        # Hydration sweep: an indeterminate strip sitting exactly where
        # the position slider is, shown while the bridge reads the file.
        self._loading_bar = Progress(indeterminate=True)
        self._loading_overlay = Div(
            styles=Styles(
                position="absolute",
                left="8px",
                right="8px",
                top="50%",
                transform=Transform.translate(y="-50%"),
                height="6px",
            ),
            container=[_mount(self._loading_bar)],
        )
        self._loading_overlay.bind_visible(self._loading)
        self._loading_bar.bind_visible(self._loading)
        self._position_slider.bind_visible(Computed(lambda: not self._loading()))

        self._duration_label = Text("0:00", role="secondary")
        self._duration_label.bind_text(self._duration_sig, fmt=_fmt_time)

        self._mute_button = Button("", variant="ghost", icon=_VOLUME_UP_ICON)
        self._mute_button.reset_styles(_MEDIA_BUTTON)
        self._mute_button.on_click(lambda _event: self.toggle_muted())
        effect(lambda: setattr(self._mute_button, "icon", _VOLUME_OFF_ICON if self._is_muted() else _VOLUME_UP_ICON))

        self._volume_slider = Slider("", min=0.0, max=1.0, step=0.05, value=1.0)
        self._volume_slider.on_input(self._on_volume_input)

        return Div(
            styles=Styles(
                display="flex",
                align_items="center",
                gap="8px",
                padding="4px 10px",
                background_color=stub.surface_raised,
            ),
            container=[
                _mount(self._play_button),
                _mount(self._time_label),
                Div(
                    styles=Styles(
                        display="flex",
                        flex_grow="1",
                        min_width="0",
                        position="relative",
                        height="22px",
                        align_items="center",
                    ),
                    container=[_mount(self._position_slider), self._loading_overlay],
                ),
                _mount(self._duration_label),
                _mount(self._mute_button),
                Div(
                    styles=Styles(display="flex", width="72px", min_width="72px"),
                    container=[_mount(self._volume_slider)],
                ),
            ],
        )

    # ---- transport callbacks ----

    def _on_scrub_input(self, event) -> None:
        self._scrubbing = True
        percent = float(event.value or 0)
        duration = self._duration_sig()
        if duration > 0:
            target = percent / 100.0 * duration
            self._time_sig.set(target)
            self._schedule_js(f"window.neony.mediaSeek({self._media_key()}, {target!r})")

    def _on_scrub_change(self, event) -> None:
        self._scrubbing = False
        percent = float(event.value or 0)
        duration = self._duration_sig()
        if duration > 0:
            self._schedule_js(f"window.neony.mediaSeek({self._media_key()}, {percent / 100.0 * duration!r})")

    def _on_volume_input(self, event) -> None:
        try:
            volume = float(event.value)
        except (TypeError, ValueError):
            return
        self._schedule_js(f"window.neony.mediaSetVolume({self._media_key()}, {volume!r})")


class Video(_MediaBase):
    """A themed video player with a custom transport row.

    - ``src`` — a built URL string: ``local_url(path)`` for local files
      (hydrated automatically), or any ``https://``/``data:`` URL.
    - ``poster`` — placeholder image URL shown before playback.
    - ``width`` / ``height`` — frame dimensions (int → px).
    - ``radius`` — corner radius of the themed frame.
    - ``autoplay`` / ``loop`` / ``muted`` / ``preload`` — native semantics;
      note browsers block audible autoplay unless ``muted=True``.

    Commands: :meth:`play` / :meth:`pause` / :meth:`seek` /
    :meth:`set_muted` / :meth:`toggle_muted` / :meth:`set_volume`.
    Events: ``on_play`` / ``on_pause`` / ``on_ended`` / ``on_timeupdate``
    / ``on_error``.  Bind the source with :meth:`bind_src`.
    """

    def __init__(
        self,
        src: str,
        *,
        poster: str | None = None,
        width: str | int | None = None,
        height: str | int | None = None,
        radius: str = "12px",
        autoplay: bool = False,
        loop: bool = False,
        muted: bool = False,
        preload: _Preload = "metadata",
    ) -> None:
        super().__init__(src, autoplay=autoplay, loop=loop, muted=muted, preload=preload)

        data_attrs: dict[str, str] = {"data-neony-direct-events": ",".join(_DIRECT_EVENTS)}
        native_kwargs: dict = {
            "preload": preload,
            "autoplay": autoplay,
            "loop": loop,
            "muted": muted,
        }
        if poster:
            native_kwargs["poster"] = poster

        self._media = DomVideo(
            styles=Styles(width="100%", display="block"),
            args=data_attrs,
            **native_kwargs,
        )
        self._bind_direct_events()
        self._root = Div(
            styles=Styles(
                border_radius=radius,
                overflow="hidden",
                background_color=stub.surface_raised,
                width=_dim(width),
                height=_dim(height),
            ),
            container=[self._media, self._transport_row()],
        )
        self._schedule_source_resolution()


class Audio(_MediaBase):
    """A themed audio player card with a custom transport row.

    Same ownership model and API as :class:`Video`; the visual is a
    compact control card instead of a picture.
    """

    def __init__(
        self,
        src: str,
        *,
        width: str | int | None = None,
        radius: str = "10px",
        media_styles: Styles | None = None,
        autoplay: bool = False,
        loop: bool = False,
        muted: bool = False,
        preload: _Preload = "metadata",
    ) -> None:
        super().__init__(src, autoplay=autoplay, loop=loop, muted=muted, preload=preload)

        data_attrs: dict[str, str] = {
            "data-neony-direct-events": ",".join(_DIRECT_EVENTS),
            # Route playback through the WebAudio engine: the shared
            # HTMLMediaElement audio chain in WebKitGTK goes silent for
            # tens of seconds when a page's second source change lands
            # (corked stream, decoder misalignment).  Decoded-buffer
            # playback sidesteps that pipeline class entirely.
            "data-neony-media-engine": "webaudio",
        }
        native_kwargs: dict = {
            "preload": preload,
            "autoplay": autoplay,
            "loop": loop,
            "muted": muted,
        }

        self._media = DomAudio(args=data_attrs, styles=Styles(), **native_kwargs)
        if media_styles is not None:
            self._media.styles = _merge_styles(self._media.styles, media_styles)
        self._bind_direct_events()
        self._root = Div(
            styles=Styles(
                border_radius=radius,
                background_color=stub.surface_raised,
                border=f"1px solid {stub.border}",
                padding="2px 4px",
                width=_dim(width),
            ),
            container=[self._media, self._transport_row()],
        )
        self._schedule_source_resolution()

    @property
    def _frame(self) -> DOMElement:
        return self._root
