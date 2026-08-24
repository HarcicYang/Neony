"""Media codec compatibility layer.

WebKitGTK's media pipeline only decodes what the host GStreamer install
supports — on stock Linux setups HEVC (H.265) is absent, so such videos
fail with ``SRC_NOT_SUPPORTED`` and never produce metadata (no poster
frame, no duration).  This module detects that situation and provides a
transparent transcode fallback using the static ffmpeg binary shipped
with ``imageio-ffmpeg`` (no system dependency).

Detection strategy (best → cheapest):
1. **WebView probe** — once a page is armed, ask the actual rendering
   engine via ``canPlayType``; this is authoritative for what will play.
2. **GStreamer caps** — enumerate decoder factories and look for an
   ``video/x-h265`` sink capability; works headlessly before any window
   exists.
3. If neither channel is available, assume *unsupported* (safe: we then
   transcode, which always plays).

File-level detection is done by parsing the MP4 ``stsd`` box directly —
no ffprobe needed (imageio-ffmpeg ships ffmpeg, not ffprobe).
"""

from __future__ import annotations

import asyncio
import logging
import shutil
import struct
from pathlib import Path

logger = logging.getLogger("neony.media_compat")

__all__ = [
    "ensure_playable_source",
    "hevc_supported",
    "set_webview_probe",
]

#: Process-wide result of the last support check (None = unknown).
_hevc_supported: bool | None = None

#: Callback that returns a coroutine evaluating to True/False/None,
#: or None when no window is armed yet.
_webview_probe = None


def set_webview_probe(probe) -> None:
    """Install the WebView ``canPlayType`` probe callback."""
    global _webview_probe
    _webview_probe = probe


def hevc_supported() -> bool | None:
    """Return cached HEVC support verdict (None = not yet probed)."""
    return _hevc_supported


# ---------------------------------------------------------------------------
# GStreamer fallback probe
# ---------------------------------------------------------------------------


def _gstreamer_supports_h265() -> bool | None:
    try:
        import gi  # pyrefly: ignore[missing-import]

        gi.require_version("Gst", "1.0")
        from gi.repository import Gst  # pyrefly: ignore[missing-import]
    except (ImportError, ValueError, KeyError):
        return None
    Gst.init(None)
    registry = Gst.Registry.get()
    for factory in registry.get_feature_list(Gst.ElementFactory):
        if not (factory.get_klass() or "").startswith("Decoder"):
            continue
        for tpl in factory.get_static_pad_templates():
            if tpl.direction != Gst.PadDirection.SINK:
                continue
            caps = tpl.get_caps()
            if caps is None:
                continue
            for i in range(caps.get_size()):
                name = caps.get_structure(i).get_name()
                if name in ("video/x-h265", "video/x-h265-profile"):
                    return True
    return False


def _sync_hevc_check() -> bool:
    global _hevc_supported
    if _hevc_supported is not None:
        return _hevc_supported
    gst_result = _gstreamer_supports_h265()
    if gst_result is not None:
        _hevc_supported = gst_result
        logger.info("HEVC support (GStreamer probe): %s", gst_result)
    else:
        _hevc_supported = False
        logger.info("HEVC support: assumed False (no probe channel)")
    return _hevc_supported


async def _async_hevc_check() -> bool:
    global _hevc_supported
    if _hevc_supported is not None:
        return _hevc_supported
    if _webview_probe is not None:
        try:
            coro = _webview_probe()
            if coro is not None:
                result = await coro
                if result is not None:
                    _hevc_supported = bool(result)
                    logger.info("HEVC support (WebView canPlayType): %s", _hevc_supported)
                    return _hevc_supported
        except Exception:
            logger.debug("WebView HEVC probe failed; falling back", exc_info=True)
    return _sync_hevc_check()


# ---------------------------------------------------------------------------
# MP4 codec sniffing
# ---------------------------------------------------------------------------


def _mp4_video_codec(path: Path) -> str | None:
    """Parse MP4 boxes to find stsd four-cc. Returns "h264"/"hevc"/None."""
    try:
        data = path.read_bytes()
    except OSError:
        return None
    if len(data) < 16 or data[4:8] != b"ftyp":
        return None

    def walk(buf, start, end, depth):
        pos = start
        while pos + 8 <= end:
            size = struct.unpack_from(">I", buf, pos)[0]
            box_type = buf[pos + 4 : pos + 8]
            header_size = 8
            if size == 0:
                size = end - pos
            elif size == 1:
                if pos + 16 > end:
                    break
                size = struct.unpack_from(">Q", buf, pos + 8)[0]
                header_size = 16
            if size < header_size or pos + size > end:
                break
            body_start = pos + header_size
            if box_type in (b"moov", b"trak", b"mdia", b"minf", b"stbl"):
                result = walk(buf, body_start, pos + size, depth + 1)
                if result:
                    return result
            elif box_type == b"stsd":
                if body_start + 8 > end:
                    return None
                count = struct.unpack_from(">I", buf, body_start + 4)[0]
                offset = body_start + 8
                for _ in range(min(count, 8)):
                    if offset + 8 > end:
                        break
                    esize = struct.unpack_from(">I", buf, offset)[0]
                    fourcc = buf[offset + 4 : offset + 8]
                    if fourcc in (b"avc1", b"avc3"):
                        return "h264"
                    if fourcc in (b"hvc1", b"hev1"):
                        return "hevc"
                    offset += max(esize, 8)
                return None
            pos += size
        return None

    return walk(data, 0, len(data), 0)


# ---------------------------------------------------------------------------
# Transcode fallback
# ---------------------------------------------------------------------------


def _ffmpeg_exe():
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        pass
    return shutil.which("ffmpeg")


_transcode_lock = asyncio.Lock()


async def ensure_playable_source(src: str) -> str:
    """Return a guaranteed-playable URL for *src*.

    For local MP4 files whose video codec the WebView cannot decode,
    transparently transcodes to H.264 and caches next to the original.
    Everything else passes through unchanged."""
    if not src.startswith("neony://local/"):
        return src

    from urllib.parse import unquote, urlparse

    parsed = urlparse(src)
    file_path = Path(unquote(parsed.path))
    if not file_path.is_file():
        return src

    codec = _mp4_video_codec(file_path)
    if codec != "hevc":
        return src

    supported = await _async_hevc_check()
    if supported:
        return src

    out_path = file_path.with_suffix(".transcoded.mp4")
    if out_path.is_file() and out_path.stat().st_size > 0:
        from neony.application.urls import local_url

        return local_url(out_path)

    exe = _ffmpeg_exe()
    if exe is None:
        logger.warning("HEVC video but no ffmpeg available; passing through")
        return src

    async with _transcode_lock:
        if out_path.is_file() and out_path.stat().st_size > 0:
            pass
        else:
            logger.info("Transcoding HEVC video %s → H.264 …", file_path.name)
            cmd = [
                exe,
                "-y",
                "-hide_banner",
                "-loglevel",
                "error",
                "-i",
                str(file_path),
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-crf",
                "23",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "copy",
                "-movflags",
                "+faststart",
                str(out_path),
            ]
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr_data = await proc.communicate()
            if proc.returncode != 0:
                logger.error(
                    "Transcode failed (%d): %s",
                    proc.returncode,
                    stderr_data.decode(errors="replace")[:500],
                )
                out_path.unlink(missing_ok=True)
                return src

    from neony.application.urls import local_url

    return local_url(out_path)
