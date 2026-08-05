"""Wayland blur entry point (``_linux_blur.apply_wayland_blur``).

Compositors that blur transparent windows on their own (Hyprland with
``decoration:blur:enabled``) must be skipped: requesting
``ext-background-effect-v1`` switches the surface onto the protocol
pipeline and *removes* the blur it already has.  Other compositors
(KWin) go through the full protocol path.
"""

from neony.application import _linux_blur


def test_hyprland_skips_protocol(monkeypatch) -> None:
    """Hyprland keeps its default blur — no protocol round-trips happen."""
    monkeypatch.setenv("WAYLAND_DISPLAY", "wayland-0")
    monkeypatch.setenv("XDG_CURRENT_DESKTOP", "Hyprland")
    probed = []
    monkeypatch.setattr(_linux_blur, "_load_libs", lambda: probed.append("load") or True)
    monkeypatch.setattr(_linux_blur, "_probe_globals", lambda: probed.append("probe") or (None, None))

    assert _linux_blur.apply_wayland_blur(object()) is True
    assert probed == [], "Hyprland must not touch the Wayland connection"


def test_kwin_goes_through_protocol_path(monkeypatch) -> None:
    """KWin has no default blur — the normal probe path is used."""
    monkeypatch.setenv("WAYLAND_DISPLAY", "wayland-0")
    monkeypatch.setenv("XDG_CURRENT_DESKTOP", "KDE")
    monkeypatch.setattr(_linux_blur, "_load_libs", lambda: True)
    monkeypatch.setattr(_linux_blur, "_probe_globals", lambda: (None, None))

    # No compositor globals -> no blur, but the protocol path was taken.
    assert _linux_blur.apply_wayland_blur(object()) is False


def test_multi_valued_desktop_uses_first(monkeypatch) -> None:
    """XDG_CURRENT_DESKTOP may be a colon-separated list."""
    monkeypatch.setenv("WAYLAND_DISPLAY", "wayland-0")
    monkeypatch.setenv("XDG_CURRENT_DESKTOP", "Hyprland:GNOME")
    monkeypatch.setattr(_linux_blur, "_load_libs", lambda: True)
    monkeypatch.setattr(_linux_blur, "_probe_globals", lambda: (None, None))

    assert _linux_blur.apply_wayland_blur(object()) is True


def test_no_wayland_session_returns_false(monkeypatch) -> None:
    """Without WAYLAND_DISPLAY the window keeps its transparency, unblurred."""
    monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)
    monkeypatch.delenv("XDG_CURRENT_DESKTOP", raising=False)

    assert _linux_blur.apply_wayland_blur(object()) is False
