#!/usr/bin/env python3
"""Custom protocols demo — local media over ``neony://local`` plus a tiny
dynamic protocol.

WebViews refuse ``file://`` subresources when the page is loaded from an
HTML string, so local media must travel over a registered custom scheme.
This demo registers Neony's built-in ``local_files`` handler and streams
whatever media sits in a folder (pass one as the first argument,
default: CWD).  A second, two-line protocol (``stamp``) serves a freshly
generated SVG image — custom protocols are just Python functions.

    uv run demo_protocols.py ~/Music
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

from neony.application import Page, launch, local_files, local_url, protocol, protocol_url
from neony.application.elements import Audio, Button, Flex, Heading, Text, Video
from neony.application.protocols import Request, Response
from neony.dom import Computed, Img, Signal

AUDIO = {".mp3", ".m4a", ".wav", ".ogg", ".oga", ".flac", ".opus"}
VIDEO = {".mp4", ".webm", ".mkv", ".mov", ".avi"}
IMAGE = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".bmp"}
MEDIA = AUDIO | VIDEO | IMAGE


# A complete custom protocol in six lines: neony://stamp/<anything>
# answers with an SVG stamp generated at request time.
@protocol("stamp")
def stamp(request: Request) -> Response:
    now = datetime.now().strftime("%H:%M:%S")
    svg = (
        "<svg xmlns='http://www.w3.org/2000/svg' width='260' height='64'>"
        "<rect width='100%' height='100%' rx='14' fill='#20293a'/>"
        "<text x='50%' y='58%' fill='#8ab4ff' font-size='20' text-anchor='middle' "
        f"font-family='monospace'>neony:// · {now}</text></svg>"
    )
    return Response(body=svg.encode("utf-8"), headers={"Content-Type": "image/svg+xml"})


def kind_of(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in VIDEO:
        return "video"
    if suffix in AUDIO:
        return "audio"
    return "image"


def write_test_tone() -> Path:
    """Synthesize a short 440 Hz WAV so the demo is playable out of the
    box — no media files needed to verify ``neony://local`` audio."""
    import math
    import tempfile
    import wave

    rate = 22050
    duration = 3 * rate // 2  # 1.5 s
    fade = rate // 20  # 50 ms fade-in/out against clicks
    frames = bytearray()
    for i in range(duration):
        amplitude = min(1.0, i / fade, (duration - i) / fade)
        sample = int(32000 * amplitude * math.sin(2 * math.pi * 440 * i / rate))
        frames += sample.to_bytes(2, "little", signed=True)
    path = Path(tempfile.mkdtemp(prefix="neony-demo-")) / "protocol-test-tone.wav"
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(rate)
        wav.writeframes(bytes(frames))
    return path


folder = Path(sys.argv[1]).expanduser().resolve() if len(sys.argv) > 1 else Path.cwd()
scanned = (
    sorted(
        (p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in MEDIA),
        key=lambda p: p.name.lower(),
    )[:12]
    if folder.is_dir()
    else []
)
media_files = [write_test_tone(), *scanned]

selected: Signal[Path | None] = Signal(None)
selected_src: Signal[str] = Signal("")

player = Video("", width=480, preload="metadata")
music = Audio("", preload="metadata")
player.bind_src(selected_src)
music.bind_src(selected_src)
picture = Img(width=320)

show_video = Computed(lambda: selected() is not None and kind_of(selected()) == "video")  # type: ignore[arg-type]
show_audio = Computed(lambda: selected() is not None and kind_of(selected()) == "audio")  # type: ignore[arg-type]
show_image = Computed(lambda: selected() is not None and kind_of(selected()) == "image")  # type: ignore[arg-type]
player.bind_visible(show_video)
music.bind_visible(show_audio)
picture.bind_visible(show_image)


def make_opener(path: Path):
    def open_media(_event) -> None:
        src = local_url(path)  # → "neony://local/<abs-path>"
        selected_src.set(src)
        picture.src = src
        selected.set(path)

    return open_media


buttons = [Button(p.name) for p in media_files]
for button, path in zip(buttons, media_files, strict=True):
    button.on_click(make_opener(path))

children: list = [
    Heading("Custom protocols", level=2),
    Text(
        f"Serving {folder} over neony://local — "
        + ("pick a file:" if buttons else "only the generated test tone is available."),
        role="secondary",
    ),
    player,
    music,
    picture,
    Heading("A dynamic protocol", level=3),
    Text('This image is generated per request by @protocol("stamp"):', role="secondary"),
    Img(src=protocol_url("stamp", "demo"), width=260),
]
if buttons:
    children.insert(2, Flex(*buttons, direction="row", wrap="wrap", gap="8px", justify="flex-start"))

page = Page(gap="16px").add(*children)

launch(page, title="Neony protocols", width=640, height=560, protocols=[local_files, stamp], devtools=True)
