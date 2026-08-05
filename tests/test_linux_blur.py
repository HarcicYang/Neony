"""Wayland blur entry point (``_linux_blur.apply_wayland_blur``).

Compositors that blur transparent windows on their own (Hyprland with
``decoration:blur:enabled``) must be skipped: requesting
``ext-background-effect-v1`` switches the surface onto the protocol
pipeline and *removes* the blur it already has.  Hyprland is detected
three ways — ``HYPRLAND_INSTANCE_SIGNATURE`` (fast path, injected by
the compositor), ``XDG_CURRENT_DESKTOP`` (fallback), and ``hyprland_*``
registry globals (protocol-level backstop for stripped environments).
Other compositors (KWin) go through the full protocol path.
"""

import ctypes
from typing import cast

import pytest
from lumiview import Window
from lumiview._core import WindowHandleKind

from neony.application import _linux_blur as blur


def _as_window(win: object) -> Window:
    """Typing shim — tests pass stand-ins where lumiview's Window is expected."""
    return cast(Window, win)


@pytest.fixture(autouse=True)
def _clean_applied(monkeypatch):
    """_APPLIED_SURFACES is process-global — reset around each test."""
    blur._APPLIED_SURFACES.clear()
    yield
    blur._APPLIED_SURFACES.clear()


# ---------------------------------------------------------------------------
# Hyprland skip — three detection layers
# ---------------------------------------------------------------------------


def test_hyprland_signature_skips_protocol(monkeypatch) -> None:
    """HYPRLAND_INSTANCE_SIGNATURE (injected by Hyprland, survives
    stripped environments) → no protocol round-trips happen."""
    monkeypatch.setenv("WAYLAND_DISPLAY", "wayland-0")
    monkeypatch.setenv("HYPRLAND_INSTANCE_SIGNATURE", "abcdef123456")
    monkeypatch.setenv("XDG_CURRENT_DESKTOP", "KDE")  # irrelevant — signature wins
    probed: list[str] = []
    monkeypatch.setattr(blur, "_load_libs", lambda: probed.append("load") or True)
    monkeypatch.setattr(blur, "_probe_globals", lambda: probed.append("probe") or (None, None, False))

    assert blur.apply_wayland_blur(_as_window(object())) is True
    assert probed == [], "Hyprland must not touch the Wayland connection"


def test_hyprland_desktop_skips_protocol(monkeypatch) -> None:
    """XDG_CURRENT_DESKTOP=Hyprland — fallback when the signature is absent."""
    monkeypatch.setenv("WAYLAND_DISPLAY", "wayland-0")
    monkeypatch.delenv("HYPRLAND_INSTANCE_SIGNATURE", raising=False)
    monkeypatch.setenv("XDG_CURRENT_DESKTOP", "Hyprland")
    probed: list[str] = []
    monkeypatch.setattr(blur, "_load_libs", lambda: probed.append("load") or True)
    monkeypatch.setattr(blur, "_probe_globals", lambda: probed.append("probe") or (None, None, False))

    assert blur.apply_wayland_blur(_as_window(object())) is True
    assert probed == []


def test_multi_valued_desktop_uses_first(monkeypatch) -> None:
    """XDG_CURRENT_DESKTOP may be a colon-separated list."""
    monkeypatch.setenv("WAYLAND_DISPLAY", "wayland-0")
    monkeypatch.delenv("HYPRLAND_INSTANCE_SIGNATURE", raising=False)
    monkeypatch.setenv("XDG_CURRENT_DESKTOP", "Hyprland:GNOME")
    monkeypatch.setattr(blur, "_load_libs", lambda: True)
    monkeypatch.setattr(blur, "_probe_globals", lambda: (None, None, False))

    assert blur.apply_wayland_blur(_as_window(object())) is True


def test_hyprland_registry_globals_skips_protocol(monkeypatch) -> None:
    """Environment stripped (systemd service / SSH): the probe's
    ``hyprland_*`` global is the backstop that still skips Hyprland."""
    monkeypatch.setenv("WAYLAND_DISPLAY", "wayland-0")
    monkeypatch.delenv("HYPRLAND_INSTANCE_SIGNATURE", raising=False)
    monkeypatch.delenv("XDG_CURRENT_DESKTOP", raising=False)
    monkeypatch.setattr(blur, "_load_libs", lambda: True)
    monkeypatch.setattr(blur, "_probe_globals", lambda: (None, None, True))

    assert blur.apply_wayland_blur(_as_window(object())) is True


def test_no_wayland_session_returns_false(monkeypatch) -> None:
    """Without WAYLAND_DISPLAY the window keeps its transparency, unblurred."""
    monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)
    monkeypatch.delenv("XDG_CURRENT_DESKTOP", raising=False)
    monkeypatch.delenv("HYPRLAND_INSTANCE_SIGNATURE", raising=False)

    assert blur.apply_wayland_blur(_as_window(object())) is False


# ---------------------------------------------------------------------------
# protocol-shape regressions (anl.md bugs #1, #3, #4, #8)
# ---------------------------------------------------------------------------


def test_set_blur_region_signature_nullable_prefix() -> None:
    """set_blur_region is ``"?o"`` — libwayland walks the signature char
    by char, and a trailing '?' (``"o?"``) hits its default branch,
    silently failing the request (EINVAL)."""
    assert blur._BLUR_SURFACE_METHODS[1].signature == b"?o"


def test_get_background_effect_signature_kept() -> None:
    """get_background_effect is ``"no"`` — new_id first, then the surface."""
    assert blur._BLUR_MANAGER_METHODS[1].signature == b"no"


def test_create_region_fallback_opcode() -> None:
    """wl_compositor never had a destroy request — create_region is
    always opcode 1 (1.25 added ``release`` at 2, not a shift)."""
    assert blur._compositor_create_region == 1


def test_get_background_effect_wraps_surface_pointer(monkeypatch) -> None:
    """Bug #1 — the wl_surface* must travel through ctypes varargs as a
    c_void_p; a bare int truncates to 32 bits."""
    calls: list[tuple] = []
    monkeypatch.setattr(blur, "_marshal_flags", lambda *args: calls.append(args) or 123)

    result = blur._get_background_effect(9, 0x1234)

    assert result == 123
    args = calls[0]
    assert args[0] == 9 and args[1] == 1  # manager proxy, get_background_effect
    assert args[2] == ctypes.addressof(blur._BLUR_SURFACE_IFACE)
    assert args[4].value is None  # new_id slot (NULL → libwayland creates the proxy)
    # The surface pointer must be wrapped: a bare int would be truncated.
    assert isinstance(args[5], ctypes.c_void_p) and args[5].value == 0x1234


# ---------------------------------------------------------------------------
# full protocol path (faked compositor) — rollback + idempotence
# ---------------------------------------------------------------------------


class _Done:
    """Completed lumiview Task stand-in (``main_thread`` returns one)."""

    def __init__(self, value: object) -> None:
        self._value = value

    def result(self, timeout: float | None = None) -> object:
        return self._value


class FakeWindow:
    """Minimal lumiview-Window stand-in exposing the handle API.

    The real accessors are ``@main_thread``-wrapped (they return a
    completed Task on the main thread) — mirrored via ``_Done``.
    """

    def __init__(self, kind: WindowHandleKind, handle: int) -> None:
        self._kind = kind
        self._handle = handle

    def native_handle_kind(self) -> _Done:
        return _Done(self._kind)

    def native_handle(self) -> _Done:
        return _Done(self._handle)


def _pipeline(
    monkeypatch: pytest.MonkeyPatch,
    *,
    window: FakeWindow | None = None,
    display_error: int = 0,
) -> tuple[bool, list[int], list[int], list[tuple]]:
    """Drive the full protocol path with a faked compositor.

    Returns ``(result, effects, commits, rollbacks)`` — the outcome plus
    the recorded ``get_background_effect`` / ``commit`` calls and
    rollback args.
    """
    if window is None:
        window = FakeWindow(WindowHandleKind.Wayland, 0x6000)
    effects: list[int] = []
    commits: list[int] = []
    rollbacks: list[tuple] = []

    monkeypatch.setenv("WAYLAND_DISPLAY", "wayland-0")
    monkeypatch.delenv("HYPRLAND_INSTANCE_SIGNATURE", raising=False)
    monkeypatch.setenv("XDG_CURRENT_DESKTOP", "KDE")
    monkeypatch.setattr(blur, "_load_libs", lambda: True)
    monkeypatch.setattr(blur, "_probe_globals", lambda: (2, 3, False))
    monkeypatch.setattr(blur, "_wayland_display", lambda: 10)
    monkeypatch.setattr(blur, "_new_registry", lambda display: 20)
    monkeypatch.setattr(blur, "_roundtrip", lambda display: 0)
    monkeypatch.setattr(
        blur,
        "_bind",
        lambda registry, name, iface, iface_name, version: 30 if iface_name == "wl_compositor" else 40,
    )
    monkeypatch.setattr(blur, "_verify_blur_capabilities", lambda display, manager: True)
    monkeypatch.setattr(blur, "_create_region", lambda compositor: 50)
    monkeypatch.setattr(blur, "_get_background_effect", lambda manager, surface: effects.append(surface) or 60)
    monkeypatch.setattr(blur, "_set_blur_region", lambda blur_surface, region: None)
    monkeypatch.setattr(blur, "_commit_surface", lambda surface: commits.append(surface))
    monkeypatch.setattr(blur, "_display_error", lambda display: display_error)
    monkeypatch.setattr(blur, "_rollback", lambda d, surface, bs, region: rollbacks.append((d, surface, bs, region)))

    result = blur.apply_wayland_blur(_as_window(window))
    return result, effects, commits, rollbacks


def test_kwin_protocol_path_applies(monkeypatch) -> None:
    result, effects, commits, rollbacks = _pipeline(monkeypatch)

    assert result is True
    assert effects == [0x6000]
    assert commits == [0x6000]
    assert rollbacks == []
    assert 0x6000 in blur._APPLIED_SURFACES


def test_rejected_blur_rolls_back(monkeypatch) -> None:
    """Bug #6 — a compositor rejection after get_background_effect must
    destroy the effect + commit, or the window stays on the protocol
    pipeline with an empty blur region (zero blur)."""
    result, effects, _commits, rollbacks = _pipeline(monkeypatch, display_error=1)

    assert result is False
    assert effects == [0x6000]
    assert rollbacks == [(10, 0x6000, 60, 50)]
    assert 0x6000 not in blur._APPLIED_SURFACES


def test_non_wayland_handle_kind_refused(monkeypatch) -> None:
    """Bug #7 — only a wl_surface* (kind=Wayland) reaches the protocol."""
    win = FakeWindow(WindowHandleKind.X11, 0xABCD)

    result, _effects, commits, rollbacks = _pipeline(monkeypatch, window=win)

    assert result is False
    assert commits == []
    assert rollbacks == [(10, 0, None, 50)]  # region torn down, nothing sent


def test_no_surface_handle_refused(monkeypatch) -> None:
    win = FakeWindow(WindowHandleKind.Wayland, 0)

    result, _effects, commits, rollbacks = _pipeline(monkeypatch, window=win)

    assert result is False
    assert commits == []
    assert rollbacks == [(10, 0, None, 50)]


def test_double_apply_is_idempotent(monkeypatch) -> None:
    """A second effect object on the same surface is a fatal protocol
    error — repeat calls must be detected, not sent."""
    blur._APPLIED_SURFACES.add(0x6000)

    result, effects, _commits, rollbacks = _pipeline(monkeypatch)

    assert result is True
    assert effects == [], "get_background_effect must not be re-sent"
    assert rollbacks == [(10, 0, None, 50)]  # fresh region torn down


# ---------------------------------------------------------------------------
# listener lifetime (anl.md bug #6)
# ---------------------------------------------------------------------------


def test_capabilities_listener_persisted(monkeypatch) -> None:
    """libwayland keeps a raw pointer to the listener struct — it must
    stay alive past the call (module-level ref), or the compositor's
    capabilities event dispatches into freed memory."""
    captured: dict = {}

    class FakeWl:
        @staticmethod
        def wl_proxy_add_listener(proxy, listener, data):
            captured["listener"] = listener
            captured["proxy"] = proxy
            captured["data"] = data

    def fake_roundtrip(display) -> None:
        # the compositor sends capabilities(blur) right after the bind
        ptr = ctypes.cast(captured["listener"], ctypes.POINTER(blur._CapsListener))
        ptr.contents.capabilities(captured["data"], captured["proxy"], blur._CAPABILITY_BLUR)

    monkeypatch.setattr(blur, "_libwayland", FakeWl())
    monkeypatch.setattr(blur, "_roundtrip", fake_roundtrip)

    assert blur._verify_blur_capabilities(1, 2) is True
    assert blur._CAPS_LISTENER is not None, "listener must be kept alive module-level"


def test_no_blur_capability_rejected(monkeypatch) -> None:
    captured: dict = {}

    class FakeWl:
        @staticmethod
        def wl_proxy_add_listener(proxy, listener, data):
            captured["listener"] = listener

    def fake_roundtrip(display) -> None:
        ptr = ctypes.cast(captured["listener"], ctypes.POINTER(blur._CapsListener))
        ptr.contents.capabilities(None, 0, 0)  # flags without the blur bit

    monkeypatch.setattr(blur, "_libwayland", FakeWl())
    monkeypatch.setattr(blur, "_roundtrip", fake_roundtrip)

    assert blur._verify_blur_capabilities(1, 2) is False
