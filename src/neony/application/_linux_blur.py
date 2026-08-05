"""Wayland background blur for transparent windows.

Applies the ``ext-background-effect-v1`` Wayland protocol (wayland-protocols
staging) so the compositor blurs the desktop behind a transparent window —
the Linux counterpart of the Acrylic/Blur materials on Windows/macOS.
KWin (KDE Plasma, DDE) implements this protocol; compositors without it
keep the window transparent without a blur.  X11 has no equivalent
protocol and is intentionally unsupported.

How it works
------------
The protocol must be bound on the *same* Wayland connection that owns the
window's ``wl_surface`` — the GTK connection.  Two obstacles:

1. The blur manager's global *name* only appears in ``wl_registry.global``
   events, which GTK consumed during startup.  Global names are assigned
   by the server and are identical on every connection, so we open a
   throwaway second connection and read the announcements from it.
2. libwayland 1.24+ removed the ``wl_display_get_registry`` /
   ``wl_registry_bind`` convenience symbols.  GTK's own replacement —
   ``wl_proxy_marshal_flags`` with the exported ``wl_registry_interface``
   — is what we use here, and it also happens to create a *fresh*
   registry proxy on the GTK connection (the server announces globals to
   it again, which we ignore).

The blur region is a ``wl_region`` covering the full surface (clipped to
surface size by the compositor).  ``set_blur_region(NULL)`` *removes*
the effect in ``ext-background-effect-v1`` (unlike the older
``ext-blur-v1`` where NULL meant infinite) — passing a real region is
required, otherwise the compositor stops blurring.

Compositors that already blur transparent windows by default (Hyprland
with ``decoration:blur:enabled``) are skipped: Hyprland switches a
surface to the protocol pipeline the moment ``get_background_effect`` is
sent (its ``shouldBlur`` then depends solely on the effect region and
the global blur is bypassed), and its explicit-region blur does not
render on fully transparent windows.  The window keeps the compositor's
default blur instead — which is what it had before the protocol call.

Hyprland is detected in three layers, so the harmful call can never slip
through on a Hyprland session:

1. ``HYPRLAND_INSTANCE_SIGNATURE`` — injected by Hyprland itself, so it
   survives systemd user services / D-Bus activation / containers / SSH
   sessions (unlike ``XDG_CURRENT_DESKTOP``, which such environments
   routinely drop and which is case-sensitive free text anyway).
2. ``XDG_CURRENT_DESKTOP`` starting with ``Hyprland`` — fallback.
3. ``hyprland_*``-prefixed globals on the registry — protocol-level
   backstop for the stripped environments above.

Everything is implemented with ctypes against ``libwayland-client.so``
and ``libgdk-3.so`` — no C compilation and no Python dependencies beyond
the compositor itself.  Every step is defensive: any failure returns
``False`` (the window stays transparent, just unblurred) and never
raises.  Once the effect object exists, every failure path rolls it
back (destroy + commit), because the pipeline switch is one-way until
the effect is destroyed *and* the surface committed.
"""

from __future__ import annotations

import ctypes
import logging
import os
import socket
import struct
from typing import Any, ClassVar

from lumiview import Window
from lumiview._core import WindowHandleKind

_LOGGER = logging.getLogger("neony.app.blur")

_BLUR_MANAGER_IFACE_NAME = "ext_background_effect_manager_v1"

# Client-side new_id values start at 2 — 0 is the null object and 1 is
# the wl_display itself.  The probe connection's registry is its first
# object, hence id 2.  (libwayland 1.24+ "stable ids" changed id reuse,
# not the starting value.)
_PROBE_REGISTRY_ID = 2

# ``wl_display.get_registry`` opcode.
_WL_DISPLAY_GET_REGISTRY = 1
# ``wl_registry.bind`` opcode.
_WL_REGISTRY_BIND = 0

# Huge region that covers any window — the compositor clips it to the
# actual surface size (``ext-background-effect-v1`` spec: "clipped by
# the compositor to the surface size").
_BLUR_REGION_SIZE = 100_000


# ---------------------------------------------------------------------------
# ctypes mirror of the Wayland wire structs we marshal
# ---------------------------------------------------------------------------


class _WlMessage(ctypes.Structure):
    """``struct wl_message`` — name, signature, argument interface types."""

    _fields_: ClassVar = [
        ("name", ctypes.c_char_p),
        ("signature", ctypes.c_char_p),
        ("types", ctypes.c_void_p),
    ]


class _WlInterface(ctypes.Structure):
    """``struct wl_interface`` — name, version, methods, events.

    Reading instances back (``from_address``) relies on ctypes' native
    alignment — the C struct has 4 bytes of padding after ``event_count``
    on 64-bit, which a manual ``struct.unpack`` would get wrong.
    """

    _fields_: ClassVar = [
        ("name", ctypes.c_char_p),
        ("version", ctypes.c_int),
        ("method_count", ctypes.c_int),
        ("methods", ctypes.POINTER(_WlMessage)),
        ("event_count", ctypes.c_int),
        ("events", ctypes.POINTER(_WlMessage)),
    ]


class _WlArgument(ctypes.Union):
    """``union wl_argument`` — one value slot for any argument type."""

    _fields_: ClassVar = [
        ("i", ctypes.c_int32),
        ("u", ctypes.c_uint32),
        ("f", ctypes.c_int32),
        ("s", ctypes.c_char_p),
        ("o", ctypes.c_void_p),
        ("n", ctypes.c_uint32),
        ("a", ctypes.c_void_p),
        ("h", ctypes.c_int32),
    ]


# Message signatures follow wayland-scanner output: 'n' = new_id,
# 'o' = object, '?' = nullable *before* the type it applies to, 's' =
# string, 'u' = uint32, 'i' = int32.  libwayland walks the signature
# character by character — a misplaced '?' falls into its ``default``
# branch and the request silently fails (EINVAL).  Events MUST be
# declared — libwayland fails dispatching beyond ``event_count``.

# ---- ext_background_effect_manager_v1 ----
# destroy=0  get_background_effect=1 ("no": new_id, wl_surface)
# event: capabilities
_BLUR_MANAGER_METHODS = (_WlMessage * 2)(
    _WlMessage(b"destroy", b"", None),
    _WlMessage(b"get_background_effect", b"no", None),
)
_BLUR_MANAGER_EVENTS = (_WlMessage * 1)(_WlMessage(b"capabilities", b"u", None))
_BLUR_MANAGER_IFACE = _WlInterface(
    _BLUR_MANAGER_IFACE_NAME.encode(), 1, 2, _BLUR_MANAGER_METHODS, 1, _BLUR_MANAGER_EVENTS
)

# ---- ext_background_effect_surface_v1 ----
# destroy=0  set_blur_region=1 ("?o" — nullable wl_region)
_BLUR_SURFACE_METHODS = (_WlMessage * 2)(
    _WlMessage(b"destroy", b"", None),
    _WlMessage(b"set_blur_region", b"?o", None),
)
_BLUR_SURFACE_IFACE = _WlInterface(b"ext_background_effect_surface_v1", 1, 2, _BLUR_SURFACE_METHODS, 0, None)

# Bit 1 of the capabilities bitfield = the compositor applies blur.
_CAPABILITY_BLUR = 1

# Compositors that blur transparent windows on their own (no protocol
# call needed).  For these the protocol call is harmful: the compositor
# switches the surface to the protocol pipeline and stops applying its
# global default blur (Hyprland: ``shouldBlur`` returns
# ``!m_blurRegion.empty()`` once a background effect exists, bypassing
# ``decoration:blur``), and its explicit-region blur does not render on
# fully transparent windows — the window loses the blur it used to have.
_BLURRED_DEFAULT_COMPOSITORS = frozenset({"Hyprland"})


# ---------------------------------------------------------------------------
# lib loading (lazy — non-Linux sessions never touch this)
# ---------------------------------------------------------------------------

_libwayland: ctypes.CDLL | None = None
_libgdk: ctypes.CDLL | None = None
_wl_registry_interface: int | None = None
_wl_compositor_interface: int | None = None
_wl_region_interface: int | None = None
_wl_surface_interface: int | None = None
_compositor_create_region: int = 1  # wl_compositor: create_surface=0, create_region=1 (release=2 since v6)
_region_add: int = 1
_surface_commit: int = 6

# Surfaces that successfully received the effect.  The protocol raises a
# fatal ``background_effect_exists`` error (it kills the connection) if
# the same surface is given an effect object twice, so re-application
# must be detected instead of sent.
_APPLIED_SURFACES: set[int] = set()

# The capabilities listener struct.  libwayland keeps a raw pointer to
# the listener for event dispatch; without a strong Python reference it
# would be freed as soon as ``_verify_blur_capabilities`` returns
# (use-after-free when the compositor dispatches to it).  The manager
# proxy lives for the process lifetime, so the listener does too.
_CAPS_LISTENER: _CapsListener | None = None


def _interface_methods(iface_ptr: int) -> dict[str, int]:
    """Map method names to opcodes for a libwayland ``wl_interface``.

    libwayland 1.25 reordered some core interfaces (``wl_compositor``
    gained ``release``, ``wl_surface`` gained ``damage_buffer``, ...),
    so opcodes are resolved from the built-in definitions instead of
    hardcoded.
    """
    iface = _WlInterface.from_address(iface_ptr)
    methods: dict[str, int] = {}
    for i in range(iface.method_count):
        msg = iface.methods[i]
        methods[msg.name.decode() if msg.name else ""] = i
    return methods


def _load_libs() -> bool:
    """Load libwayland-client/libgdk-3 and resolve the built-in interfaces."""
    global _libwayland, _libgdk, _wl_registry_interface, _wl_compositor_interface
    global _wl_region_interface, _wl_surface_interface
    global _compositor_create_region, _region_add, _surface_commit
    if _libwayland is not None or _libgdk is not None:
        return _libwayland is not None and _libgdk is not None
    try:
        _libwayland = ctypes.CDLL("libwayland-client.so.0")
        _libgdk = ctypes.CDLL("libgdk-3.so.0")
        # The exported data symbols resolve via dlsym (ctypes.in_dll
        # returns a misaligned address on some distros).
        libdl = ctypes.CDLL("libdl.so.2")
        libdl.dlsym.restype = ctypes.c_void_p
        libdl.dlsym.argtypes = [ctypes.c_void_p, ctypes.c_char_p]

        def sym(name: str) -> int | None:
            return libdl.dlsym(None, name.encode())

        _wl_registry_interface = sym("wl_registry_interface")
        _wl_compositor_interface = sym("wl_compositor_interface")
        _wl_region_interface = sym("wl_region_interface")
        _wl_surface_interface = sym("wl_surface_interface")

        # Resolve opcodes from the built-in layouts (defensive fallbacks
        # keep the classic values when resolution fails).
        if _wl_compositor_interface:
            _compositor_create_region = _interface_methods(_wl_compositor_interface).get("create_region", 1)
        if _wl_region_interface:
            _region_add = _interface_methods(_wl_region_interface).get("add", 1)
        if _wl_surface_interface:
            _surface_commit = _interface_methods(_wl_surface_interface).get("commit", 6)
    except OSError:
        _libwayland = _libgdk = None
        _wl_registry_interface = _wl_compositor_interface = None
        _wl_region_interface = _wl_surface_interface = None
        _LOGGER.debug("Wayland blur: libwayland-client/libgdk-3 not available")
    return _libwayland is not None and _libgdk is not None and _wl_registry_interface is not None


def _marshal_flags(proxy: int, opcode: int, iface: int | None, version: int, *args: Any) -> int | None:
    """Send one request via ``wl_proxy_marshal_flags`` (varargs form).

    ``args`` are the request arguments; a ``new_id`` slot must be passed
    as ``ctypes.c_void_p(0)`` — libwayland creates the proxy itself.
    Every pointer argument must be wrapped in ``ctypes.c_void_p`` too:
    ctypes converts bare Python ints in varargs to 32-bit C ints, which
    truncates 64-bit pointers.  Returns the new proxy pointer for
    messages with a ``new_id``, else NULL-ish.
    """
    wl = _libwayland
    assert wl is not None
    wl.wl_proxy_marshal_flags.restype = ctypes.c_void_p
    wl.wl_proxy_marshal_flags.argtypes = [
        ctypes.c_void_p,
        ctypes.c_uint32,
        ctypes.c_void_p,
        ctypes.c_uint32,
        ctypes.c_uint32,
    ]
    return wl.wl_proxy_marshal_flags(proxy, opcode, iface, version, 0, *args) or None


def _marshal_array(proxy: int, opcode: int, iface: int, args: Any) -> int | None:
    """Send one request via ``wl_proxy_marshal_array_flags``.

    Passing a non-NULL *iface* avoids libwayland's fallback path that
    reads past custom interface structs.
    """
    wl = _libwayland
    assert wl is not None
    wl.wl_proxy_marshal_array_flags.restype = ctypes.c_void_p
    wl.wl_proxy_marshal_array_flags.argtypes = [
        ctypes.c_void_p,
        ctypes.c_uint32,
        ctypes.c_void_p,
        ctypes.c_uint32,
        ctypes.c_uint32,
        ctypes.c_void_p,
    ]
    return wl.wl_proxy_marshal_array_flags(proxy, opcode, iface, 0, 0, args) or None


def _roundtrip(display: int) -> int:
    """Flush pending requests and wait for the server to process them."""
    wl = _libwayland
    assert wl is not None
    wl.wl_display_roundtrip.restype = ctypes.c_int
    wl.wl_display_roundtrip.argtypes = [ctypes.c_void_p]
    return wl.wl_display_roundtrip(display)


def _display_error(display: int) -> int:
    wl = _libwayland
    assert wl is not None
    wl.wl_display_get_error.restype = ctypes.c_int
    wl.wl_display_get_error.argtypes = [ctypes.c_void_p]
    return wl.wl_display_get_error(display)


# ---------------------------------------------------------------------------
# probe connection: read the compositor & blur manager global names
# ---------------------------------------------------------------------------


def _wayland_socket_path() -> str | None:
    """Absolute path of the compositor socket from the environment."""
    display_name = os.environ.get("WAYLAND_DISPLAY")
    if not display_name:
        return None
    if display_name.startswith("/"):
        return display_name
    runtime = os.environ.get("XDG_RUNTIME_DIR")
    if not runtime:
        return None
    path = os.path.join(runtime, display_name)
    return path if os.path.exists(path) else None


def _recv_exact(sock: socket.socket, n: int) -> bytes | None:
    buf = b""
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            return None
        buf += chunk
    return buf


def _probe_globals() -> tuple[int | None, int | None, bool]:
    """Return ``(wl_compositor_name, blur_manager_name, is_hyprland)``.

    Opens a throwaway connection, sends ``wl_display.get_registry`` and
    parses ``wl_registry.global`` announcements.  Global names are
    identical on every connection, so the result applies to GTK's
    connection as well.  ``is_hyprland`` is True when any ``hyprland_*``
    private global is announced — the protocol-level backstop for
    detecting Hyprland in environments where the env vars were stripped.
    """
    path = _wayland_socket_path()
    if path is None:
        return None, None, False
    compositor_name: int | None = None
    blur_name: int | None = None
    hyprland_seen = False
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
            sock.settimeout(2.0)
            sock.connect(path)
            # wl_display.get_registry: opcode 1, body = new_id.
            # Message size = 8 (header) + 4 (new_id) = 12.
            sock.sendall(struct.pack("<III", 1, (12 << 16) | 1, _PROBE_REGISTRY_ID))
            while not (hyprland_seen or (compositor_name is not None and blur_name is not None)):
                header = _recv_exact(sock, 8)
                if header is None:
                    break
                object_id, size_opcode = struct.unpack("<II", header)
                size = size_opcode >> 16
                opcode = size_opcode & 0xFFFF
                if size < 8:
                    break
                body = _recv_exact(sock, size - 8)
                if body is None:
                    break
                if object_id == _PROBE_REGISTRY_ID and opcode == 0:
                    # registry.global: name (u32), interface (string), version (u32).
                    # String length INCLUDES the trailing NUL.
                    name = struct.unpack_from("<I", body, 0)[0]
                    slen = struct.unpack_from("<I", body, 4)[0]
                    interface = body[8 : 8 + slen].split(b"\x00", 1)[0].decode("utf-8", "replace")
                    if interface.startswith("hyprland_"):
                        hyprland_seen = True
                    elif interface == "wl_compositor":
                        compositor_name = name
                    elif interface == _BLUR_MANAGER_IFACE_NAME:
                        blur_name = name
    except (OSError, TimeoutError):
        _LOGGER.debug("Wayland blur: probe connection failed", exc_info=True)
    return compositor_name, blur_name, hyprland_seen


# ---------------------------------------------------------------------------
# the app's connection: registry → bind → region → blur surface → commit
# ---------------------------------------------------------------------------


def _wayland_display() -> int | None:
    """The app's ``wl_display*`` — the connection GTK renders on."""
    if not _load_libs():
        return None
    gdk = _libgdk
    assert gdk is not None
    gdk.gdk_display_get_default.restype = ctypes.c_void_p
    gdk.gdk_display_get_default.argtypes = []
    display = gdk.gdk_display_get_default()
    if not display:
        return None
    gdk.gdk_wayland_display_get_wl_display.restype = ctypes.c_void_p
    gdk.gdk_wayland_display_get_wl_display.argtypes = [ctypes.c_void_p]
    return gdk.gdk_wayland_display_get_wl_display(display) or None


def _new_registry(display: int) -> int | None:
    """Create a fresh ``wl_registry`` proxy on the app's connection.

    libwayland 1.24+ removed ``wl_display_get_registry``; this is GTK's
    own replacement, and the server announces globals to the new proxy
    (which we don't need to listen to).
    """
    if not _load_libs():
        return None
    return _marshal_flags(display, _WL_DISPLAY_GET_REGISTRY, _wl_registry_interface, 1, ctypes.c_void_p(0))


def _bind(registry: int, name: int, iface_addr: int | None, iface_name: str, version: int) -> int | None:
    """Bind a global on the registry (``wl_registry.bind``).  Returns the new proxy."""
    if iface_addr is None:
        return None
    return _marshal_flags(
        registry,
        _WL_REGISTRY_BIND,
        iface_addr,
        version,
        ctypes.c_uint32(name),
        ctypes.c_char_p(iface_name.encode()),
        ctypes.c_uint32(version),
        ctypes.c_void_p(0),  # new_id — libwayland creates the proxy
    )


_CAP_CALLBACK = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint32)


class _CapsListener(ctypes.Structure):
    _fields_: ClassVar = [("capabilities", _CAP_CALLBACK)]


def _verify_blur_capabilities(display: int, manager: int) -> bool:
    """Roundtrip and check whether the compositor reports blur support."""
    global _CAPS_LISTENER
    wl = _libwayland
    assert wl is not None
    caps: list[int] = []

    @_CAP_CALLBACK
    def on_capabilities(_data: int, _manager: int, flags: int) -> None:
        caps.append(flags)

    listener = _CapsListener(on_capabilities)
    _CAPS_LISTENER = listener  # keep alive: libwayland holds a raw pointer (see module comment)
    wl.wl_proxy_add_listener.restype = ctypes.c_int
    wl.wl_proxy_add_listener.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p]
    wl.wl_proxy_add_listener(manager, ctypes.byref(listener), None)
    _roundtrip(display)
    return bool(caps and caps[0] & _CAPABILITY_BLUR)


def _create_region(compositor: int) -> int | None:
    """Create a wl_region covering the whole surface.

    The compositor clips regions to surface size, so a huge fixed region
    works regardless of the actual window dimensions.
    """
    if not _load_libs() or _wl_region_interface is None:
        return None
    region = _marshal_flags(compositor, _compositor_create_region, _wl_region_interface, 1, ctypes.c_void_p(0))
    if not region:
        return None
    # wl_region.add: signature "iiii" (x, y, width, height).
    args = (_WlArgument * 4)(
        _WlArgument(i=0),
        _WlArgument(i=0),
        _WlArgument(i=_BLUR_REGION_SIZE),
        _WlArgument(i=_BLUR_REGION_SIZE),
    )
    _marshal_array(region, _region_add, _wl_region_interface, args)
    return region


def _get_background_effect(manager: int, surface: int) -> int | None:
    """``get_background_effect(surface)`` → the blur surface proxy.

    *surface* is a pointer and must be wrapped in ``c_void_p`` — a bare
    Python int goes through ctypes varargs as a 32-bit C int and the
    server receives a truncated object id.
    """
    return _marshal_flags(
        manager,
        1,
        ctypes.addressof(_BLUR_SURFACE_IFACE),
        1,
        ctypes.c_void_p(0),  # new_id — libwayland creates the proxy
        ctypes.c_void_p(surface),
    )


def _set_blur_region(blur_surface: int, region: int) -> None:
    """``set_blur_region(region)`` — the compositor blurs the region behind the surface."""
    args = (_WlArgument * 1)(_WlArgument(o=region))
    _marshal_array(blur_surface, 1, ctypes.addressof(_BLUR_SURFACE_IFACE), args)


def _commit_surface(surface: int) -> None:
    """``wl_surface.commit`` — activate the double-buffered blur region.

    This runs outside GTK's own frame cycle, but only at window-creation
    time — before GTK has drawn any frame, so there is no half-built
    pending state to corrupt.  GTK's own subsequent frame commits carry
    the same pending region anyway.
    """
    if not _load_libs() or _wl_surface_interface is None:
        return
    _marshal_flags(surface, _surface_commit, _wl_surface_interface, 1)


def _rollback(display: int, surface: int, blur_surface: int | None, region: int | None) -> None:
    """Restore the pre-protocol state after a partial application.

    The pipeline switch is one-way until the effect object is destroyed
    *and* the surface committed, so any failure after the effect was
    created must tear it down again — otherwise the window stays on the
    protocol pipeline with the initial empty blur region (zero blur,
    and the compositor's own default bypassed).  Never raises.
    """
    try:
        if blur_surface is not None:
            _marshal_flags(blur_surface, 0, ctypes.addressof(_BLUR_SURFACE_IFACE), 1)
        if region is not None:
            _marshal_flags(region, 0, _wl_region_interface, 1)
        if surface:
            _commit_surface(surface)
            _roundtrip(display)
    except Exception:
        _LOGGER.debug("Wayland blur: rollback failed", exc_info=True)


def _wayland_surface(window: Window) -> int | None:
    """The window's ``wl_surface*``, verified by handle kind.

    lumiview exposes the raw handle via ``native_handle()``: on Wayland
    that is the ``wl_surface*`` itself (raw-window-handle), not a GTK
    widget pointer — confirmed against ``native_handle_kind()`` so a
    non-Wayland handle (X11 XID, GtkWindow) never reaches the protocol.
    The accessors are ``@main_thread``: they run synchronously here
    (we're on the main thread via ``call_on_main``) and their Task is
    already complete, so ``.result()`` returns instantly.
    """
    try:
        if window.native_handle_kind().result() is not WindowHandleKind.Wayland:
            _LOGGER.info("Wayland blur: window handle is not a Wayland surface")
            return None
        surface = window.native_handle().result()
    except Exception:
        _LOGGER.warning("Wayland blur: no native surface handle", exc_info=True)
        return None
    return surface or None


# ---------------------------------------------------------------------------
# public entry point
# ---------------------------------------------------------------------------


def _hyprland_by_environment() -> bool:
    """Hyprland detection from the environment (fast path, no probing).

    ``HYPRLAND_INSTANCE_SIGNATURE`` is injected by Hyprland into the
    session environment unconditionally — unlike ``XDG_CURRENT_DESKTOP``,
    which systemd user services, containers, D-Bus activation and SSH
    sessions routinely drop (and which is case-sensitive free text).
    The desktop variable stays as a fallback for derived sessions.
    """
    if os.environ.get("HYPRLAND_INSTANCE_SIGNATURE"):
        return True
    current_desktop = os.environ.get("XDG_CURRENT_DESKTOP", "")
    return current_desktop.split(":")[0] in _BLURRED_DEFAULT_COMPOSITORS


def apply_wayland_blur(window: Window) -> bool:
    """Request compositor blur behind *window* (a lumiview Window).

    Safe to call from any thread — this runs on the GTK main loop via
    ``App.call_on_main``.  Returns True when the blur was requested (or
    is already in place); False otherwise (non-Wayland session,
    compositor without the protocol, or any internal failure).  Never
    raises.
    """
    if not os.environ.get("WAYLAND_DISPLAY"):
        return False
    # Compositors with a default blur for transparent windows need no
    # protocol call — requesting one would switch the window onto the
    # protocol pipeline and *remove* the blur it already has (see
    # _BLURRED_DEFAULT_COMPOSITORS).  Keep their default behaviour.
    if _hyprland_by_environment():
        _LOGGER.info("Wayland blur: Hyprland detected — keeping its default blur")
        return True
    if not _load_libs():
        return False
    region: int | None = None
    blur_surface: int | None = None
    surface = 0
    display: int | None = None
    try:
        compositor_name, blur_name, hyprland_globals = _probe_globals()
        if hyprland_globals:
            _LOGGER.info("Wayland blur: Hyprland detected via registry globals — keeping its default blur")
            return True
        if compositor_name is None or blur_name is None:
            _LOGGER.info("Wayland blur: compositor has no wl_compositor and/or ext_background_effect_manager_v1")
            return False
        display = _wayland_display()
        if display is None:
            _LOGGER.info("Wayland blur: app is not on a Wayland GDK display")
            return False
        registry = _new_registry(display)
        if registry is None:
            _LOGGER.warning("Wayland blur: could not create wl_registry")
            return False
        _roundtrip(display)

        # Bind compositor + blur manager + region + blur surface + commit.
        compositor = _bind(registry, compositor_name, _wl_compositor_interface, "wl_compositor", 1)
        manager = _bind(registry, blur_name, ctypes.addressof(_BLUR_MANAGER_IFACE), _BLUR_MANAGER_IFACE_NAME, 1)
        if compositor is None or manager is None:
            _LOGGER.warning("Wayland blur: bind failed")
            return False
        if not _verify_blur_capabilities(display, manager):
            _LOGGER.info("Wayland blur: compositor does not apply blur")
            return False
        region = _create_region(compositor)
        if region is None:
            _LOGGER.warning("Wayland blur: could not create wl_region")
            return False
        surface = _wayland_surface(window) or 0
        if not surface:
            _LOGGER.warning("Wayland blur: no native surface handle")
            _rollback(display, 0, None, region)
            return False
        if surface in _APPLIED_SURFACES:
            _rollback(display, 0, None, region)  # region was never committed
            return True  # already blurred — idempotent
        blur_surface = _get_background_effect(manager, surface)
        if blur_surface is None:
            _LOGGER.warning("Wayland blur: get_background_effect failed")
            _rollback(display, 0, None, region)
            return False
        _set_blur_region(blur_surface, region)
        _commit_surface(surface)
        _roundtrip(display)
        if _display_error(display):
            _LOGGER.warning("Wayland blur: compositor rejected the blur request")
            _rollback(display, surface, blur_surface, region)
            return False
        _APPLIED_SURFACES.add(surface)
        _LOGGER.info("Wayland blur: applied behind window (ext-background-effect-v1)")
        return True
    except Exception:  # blur is cosmetic; never crash the app
        if display is not None:
            _rollback(display, surface, blur_surface, region)
        _LOGGER.warning("Wayland blur failed", exc_info=True)
        return False
