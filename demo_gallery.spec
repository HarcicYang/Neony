# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for ``demo_gallery.py`` (all platforms).

Linux: system GTK/WebKit libraries are EXCLUDED from the bundle.
PyInstaller would otherwise copy the build machine's copies (Ubuntu
paths), and the executable would load those — whose hardcoded helper
paths (``WebKitNetworkProcess``, ``WebKitWebProcess``) belong to the
build distro, not the target machine, so the web process fails to spawn
(``Unable to spawn a new child process ... WebKitNetworkProcess``) and
the app aborts.  The system-installed webkit2gtk is the only reliable
runtime dependency on Linux (see README-linux.md in the workflow).

Windows/macOS: WebView2 / WebKit are OS-provided and never bundled; the
native bindings (lumiview/wryview ``_core.abi3``) and the neony JS
assets are collected as usual.
"""

import os
import sys

from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs

# The neony package ships its browser engine as ``javascript/*.js`` —
# without it the page mounts to a blank screen.
datas = collect_data_files("neony")

# Native extensions: lumiview and wryview each ship a Rust ``_core``
# module built with maturin.  Their ldd dependencies are NOT collected
# here — that is Analysis' job, and the Linux pass strips them below.
binaries = collect_dynamic_libs("lumiview") + collect_dynamic_libs("wryview")

# Lazy-imported lumiview internals that static analysis cannot see.
hiddenimports = [
    "lumiview.plugins.window_controls",
    "lumiview._events",
    "lumiview._task",
]

a = Analysis(
    ["demo_gallery.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

if sys.platform == "linux":
    # Strip the GTK/WebKit/X11/Wayland stack from the bundle (see the
    # module docstring): the executable must load the target machine's
    # webkit2gtk, whose helper-process paths are distro-specific.
    _SYSTEM_PREFIXES = (
        "libwebkit",
        "libjavascriptcore",
        "libsoup",
        "libgtk",
        "libgdk",
        "libglib",
        "libgobject",
        "libgio",
        "libpango",
        "libpangocairo",
        "libcairo",
        "libgdk_pixbuf",
        "libepoxy",
        "libfontconfig",
        "libfribidi",
        "libX11",
        "libXi",
        "libXext",
        "libXcursor",
        "libXdamage",
        "libXfixes",
        "libXcomposite",
        "libwayland",
        "libxkbcommon",
        "libdbus",
    )
    a.binaries = [
        entry
        for entry in a.binaries
        if not os.path.basename(entry[1]).startswith(_SYSTEM_PREFIXES)
    ]

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="neony-gallery",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
)
