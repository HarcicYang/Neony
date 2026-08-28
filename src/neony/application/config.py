"""Pydantic configuration models for NeonApplication.

Groups LumiView's ``Window.create`` parameters into focused sub-models
so applications configure by concern instead of a single god-method
with ~50 keyword arguments.
"""

from __future__ import annotations

from typing import Any

from lumiview import CloseBehavior
from pydantic import BaseModel, Field


class WindowConfig(BaseModel):
    """Window geometry and appearance.

    Maps 1:1 to ``Window.create`` geometry/appearance keyword arguments.
    """

    title: str = "Neony"
    width: int = 800
    height: int = 600
    position: tuple[float, float] | None = None
    min_size: tuple[float, float] | None = None
    max_size: tuple[float, float] | None = None
    visible: bool = True
    # When the window hides / minimizes, also hide the underlying webview
    # so the platform can throttle it (lumiview's default).  Turn off for
    # tray-style apps that must keep rendering while hidden.
    sync_visibility: bool = True
    decorations: bool = True
    resizable: bool = True
    transparent: bool = False
    maximized: bool = False
    always_on_top: bool = False
    undecorated_shadow: bool | None = None
    icon: str | tuple[bytes, int, int] | None = None
    focused: bool = True
    focusable: bool = True
    minimizable: bool = True
    maximizable: bool = True
    closable: bool = True
    close_behavior: CloseBehavior = CloseBehavior.Close
    visible_on_all_workspaces: bool = False
    content_protection: bool = False
    background_color: tuple[int, int, int, int] | None = None


class WebViewConfig(BaseModel):
    """WebView runtime and developer options.

    Maps 1:1 to ``Window.create`` webview profile keyword arguments.
    """

    devtools: bool = False
    incognito: bool = False
    data_directory: str | None = None
    proxy: str | None = None
    user_agent: str | None = None
    autoplay: bool = False
    hotkeys_zoom: bool = True
    clipboard: bool = True
    javascript: bool = True
    back_forward_gestures: bool = False
    https_scheme: bool = True
    # Off by default: the app draws its own menus (Menu component,
    # contextmenu events) — the webview's native right-click menu would
    # cover them.  Set True for the platform default menu.
    default_context_menus: bool = False
    headers: dict[str, str] | None = None


class Config(BaseModel):
    """Top-level configuration for :class:`~neony.application.NeonApplication`."""

    window: WindowConfig = Field(default_factory=WindowConfig)
    webview: WebViewConfig = Field(default_factory=WebViewConfig)
    mount_selector: str = "body"
    auto_render: bool = True

    def to_window_kwargs(self) -> dict[str, Any]:
        """Build the keyword arguments for ``Window.create``.

        Combines :attr:`window` and :attr:`webview` fields, dropping
        any ``None`` values (so LumiView defaults apply).
        """
        kwargs: dict[str, Any] = {}
        for cfg in (self.window, self.webview):
            for name, value in cfg.model_dump().items():
                if value is not None:
                    kwargs[name] = value
        return kwargs
