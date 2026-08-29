"""WindowConfig / WebViewConfig → ``Window.create`` kwargs plumbing."""

from neony.application import Config, WindowConfig


def test_default_kwargs_include_sync_visibility():
    kwargs = Config().to_window_kwargs()
    assert kwargs["sync_visibility"] is True


def test_sync_visibility_false_passes_through():
    kwargs = Config(window=WindowConfig(sync_visibility=False)).to_window_kwargs()
    assert kwargs["sync_visibility"] is False
