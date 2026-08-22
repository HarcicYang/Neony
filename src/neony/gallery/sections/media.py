"""Media section — the themed Video / Audio players.

A file picker loads any local media file; a synthesized 440 Hz tone is
loaded at startup so the section always has something to play.
"""

from __future__ import annotations

import math
import tempfile
import wave
from collections.abc import Callable
from pathlib import Path

from neony.application import Page
from neony.application.elements import (
    Audio,
    Button,
    Heading,
    HStack,
    Separator,
    Text,
    Video,
    VStack,
)
from neony.application.urls import local_url
from neony.dom import Computed, Signal
from neony.gallery.core import Section, app, tr_now
from neony.gallery.i18n import tr

PANELS: dict[str, VStack] = {}

AUDIO_EXTS = {".mp3", ".wav", ".ogg", ".flac", ".m4a"}
VIDEO_EXTS = {".mp4", ".webm", ".mkv", ".mov", ".m4v", ".ogv"}
_MEDIA_FILETYPES = [
    ("Media", "*.mp4 *.webm *.mkv *.mov *.m4v *.ogv *.mp3 *.wav *.ogg *.flac *.m4a"),
    ("All files", "*.*"),
]


def _synth_tone(name: str = "gallery-tone.wav") -> Path:
    """Synthesize a short 440 Hz WAV so audio demos play with no media files."""
    rate = 22050
    duration = 3 * rate  # 3 s
    fade = rate // 20
    frames = bytearray()
    for i in range(duration):
        amplitude = min(1.0, i / fade, (duration - i) / fade)
        sample = int(32000 * amplitude * math.sin(2 * math.pi * 440 * i / rate))
        frames += sample.to_bytes(2, "little", signed=True)
    path = Path(tempfile.gettempdir()) / "neony-gallery-media" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(rate)
        wav.writeframes(bytes(frames))
    return path


def _fmt(seconds: float) -> str:
    total = int(max(0.0, seconds))
    minutes, secs = divmod(total, 60)
    return f"{minutes}:{secs:02d}"


# ── shared player state ──────────────────────────────────────────

_status = Signal(tr_now(tr.media.status_idle))
_src = Signal(local_url(_synth_tone()))
_show_video = Signal(False)
_loaded_name = Signal("")

_audio_player = Audio(_src(), width=480).bind_src(_src)
_video_player = Video(_src(), width=560).bind_src(_src)
_video_player.bind_visible(_show_video)
_audio_player.bind_visible(Computed(lambda: not _show_video()))


def _active() -> Audio | Video:
    return _video_player if _show_video() else _audio_player


async def _pick_media(_event: object) -> None:
    """Open the native file dialog and load the picked file."""
    chosen = await app.open_file(title=tr_now(tr.media.pick_title), filetypes=_MEDIA_FILETYPES)
    if not chosen:
        return
    path = Path(chosen)
    suffix = path.suffix.lower()
    if suffix not in AUDIO_EXTS and suffix not in VIDEO_EXTS:
        return
    # Pause before swapping the source: the old element's pause event is
    # not guaranteed to arrive during rehydration.
    await _active().pause()
    _src.set(local_url(path))
    _show_video.set(suffix in VIDEO_EXTS)
    _loaded_name.set(tr_now(tr.media.loaded_fmt).format(name=path.name))


async def _refresh_status(_event: object) -> None:
    player = _active()
    if player.playing:
        _status.set(
            tr_now(tr.media.status_playing_fmt).format(time=_fmt(player.position), duration=_fmt(player.duration))
        )


def _mark_ended(_event: object) -> None:
    _status.set(tr_now(tr.media.status_ended))


for _player in (_audio_player, _video_player):
    _player.on_timeupdate(_refresh_status).on_pause(_refresh_status).on_play(_refresh_status).on_ended(_mark_ended)

# ── transport playground ─────────────────────────────────────────


async def _toggle_play(_event: object) -> None:
    player = _active()
    if player.playing:
        await player.pause()
    else:
        await player.play()


async def _seek_back(_event: object) -> None:
    await _active().seek(max(0.0, _active().position - 10))


async def _seek_forward(_event: object) -> None:
    player = _active()
    await player.seek(min(player.duration or 0.0, player.position + 10))


async def _toggle_mute(_event: object) -> None:
    await _active().toggle_muted()


_pick_button = Button("📂 " + tr_now(tr.media.pick))
_pick_button.on_click(_pick_media)
_toggle_button = Button("⏯ Play / Pause")
_toggle_button.on_click(_toggle_play)
_back_button = Button("« 10s")
_back_button.on_click(_seek_back)
_fwd_button = Button("10s »")
_fwd_button.on_click(_seek_forward)
_mute_button = Button("🔇 Mute")
_mute_button.on_click(_toggle_mute)

PANELS["media"] = Section(
    tr.media.title,
    tr.media.blurb,
    """from neony.application.urls import local_url

song = Audio(local_url(Path("song.mp3").resolve()), width=420)
clip = Video(local_url(Path("clip.mp4").resolve()), width=560)

path = await app.open_file(filetypes=[("Media", "*.mp4 *.mp3 …")])
if path:
    src.set(local_url(Path(path)))
    song.bind_src(src)

await song.play()
await song.seek(30)
await song.toggle_muted()""",
    HStack(_pick_button, Text(_loaded_name, role="secondary"), gap="12px"),
    _video_player,
    _audio_player,
    Separator(),
    Heading(tr.media.playground_title, level=4),
    Text(tr.media.playground_blurb, role="secondary"),
    HStack(_toggle_button, _back_button, _fwd_button, _mute_button, gap="8px"),
    Text(_status, role="secondary"),
)


def _wire(page: Page) -> None:
    return None


PAGE_HOOKS: list[Callable[[Page], None]] = [_wire]
