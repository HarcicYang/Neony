"""Media demo — the themed Video / Audio components.

A file picker loads any local media file over ``neony://local``; a
synthesized 440 Hz test tone is loaded at startup so the demo is
playable out of the box.
"""

from __future__ import annotations

import math
import tempfile
import wave
from pathlib import Path

from neony.application import Config, NeonApplication, Page, WindowConfig, icons, local_files
from neony.application.elements import (
    Audio,
    Button,
    Heading,
    HStack,
    Separator,
    Text,
    Video,
)
from neony.application.urls import local_url
from neony.dom import Computed, Signal

AUDIO_EXTS = {".mp3", ".wav", ".ogg", ".flac", ".m4a"}
VIDEO_EXTS = {".mp4", ".webm", ".mkv", ".mov", ".m4v", ".ogv"}
MEDIA_FILETYPES = [
    ("Media", "*.mp4 *.webm *.mkv *.mov *.m4v *.ogv *.mp3 *.wav *.ogg *.flac *.m4a"),
    ("All files", "*.*"),
]


def write_test_tone() -> Path:
    """Synthesize a short 440 Hz WAV so the demo is playable out of the
    box — no media files needed to verify ``neony://local`` audio."""
    rate = 22050
    duration = 3 * rate // 2  # 1.5 s
    fade = rate // 20  # 50 ms fade-in/out against clicks
    frames = bytearray()
    for i in range(duration):
        amplitude = min(1.0, i / fade, (duration - i) / fade)
        sample = int(32000 * amplitude * math.sin(2 * math.pi * 440 * i / rate))
        frames += sample.to_bytes(2, "little", signed=True)
    path = Path(tempfile.mkdtemp(prefix="neony-media-demo-")) / "test-tone.wav"
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


# ── state ────────────────────────────────────────────────────────

_src = Signal(local_url(write_test_tone()))
_show_video = Signal(False)
_loaded_name = Signal("")
_status: Signal[str] = Signal("idle")

_audio_player = Audio(_src(), width=520).bind_src(_src)
_video_player = Video(_src(), width=560).bind_src(_src)
_video_player.bind_visible(_show_video)
_audio_player.bind_visible(Computed(lambda: not _show_video()))


def _active() -> Audio | Video:
    return _video_player if _show_video() else _audio_player


async def refresh(_event: object) -> None:
    player = _active()
    if player.playing:
        _status.set(f"playing · {_fmt(player.position)} / {_fmt(player.duration)}")


def mark_ended(_event: object) -> None:
    _status.set("ended")


for _player in (_audio_player, _video_player):
    _player.on_timeupdate(refresh).on_pause(refresh).on_play(refresh).on_ended(mark_ended)


async def pick(_event: object) -> None:
    chosen = await _APP.open_file(title="Choose media", filetypes=MEDIA_FILETYPES)
    if not chosen:
        return
    path = Path(chosen)
    suffix = path.suffix.lower()
    if suffix not in AUDIO_EXTS and suffix not in VIDEO_EXTS:
        return
    await _active().pause()
    _src.set(local_url(path))
    _show_video.set(suffix in VIDEO_EXTS)
    _loaded_name.set(path.name)


async def toggle(_event: object) -> None:
    player = _active()
    if player.playing:
        await player.pause()
    else:
        await player.play()


async def back(_event: object) -> None:
    await _active().seek(max(0.0, _active().position - 5))


async def forward(_event: object) -> None:
    player = _active()
    await player.seek(min(player.duration or 0.0, player.position + 5))


async def mute(_event: object) -> None:
    await _active().toggle_muted()


pick_btn = Button("Choose media file…", icon=icons.folder_open)
pick_btn.on_click(pick)
toggle_btn = Button("Play / Pause", icon=icons.play_arrow)
toggle_btn.on_click(toggle)
back_btn = Button("5s", icon=icons.chevron_left)
back_btn.on_click(back)
fwd_btn = Button("5s", icon=icons.chevron_right)
fwd_btn.on_click(forward)
mute_btn = Button("Mute", icon=icons.volume_up)
mute_btn.on_click(mute)

page = Page(gap="16px").add(
    Heading("Media components", level=2),
    Text(
        "Managed players: sources under neony:// are hydrated by the runtime; "
        "the transport row is built from regular Neony widgets — native "
        "controls are never shown.",
        role="secondary",
    ),
    Separator(),
    HStack(pick_btn, Text(_loaded_name, role="secondary"), gap="12px"),
    _video_player,
    _audio_player,
    Separator(),
    Heading("Command playground", level=3),
    HStack(toggle_btn, back_btn, fwd_btn, mute_btn, gap="8px"),
    Text(_status, role="secondary"),
)

_APP = NeonApplication(
    Config(window=WindowConfig(title="Neony media", width=760, height=680)),
    protocols=[local_files],
)
_APP.run(page)
