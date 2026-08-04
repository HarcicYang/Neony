"""App-level shutdown hook — ``app.close_handler`` registered on
lumiview's ``AppHookEvent.Close`` (fires once after all windows close,
before the asyncio loop stops; completion is awaited by lumiview)."""

import asyncio

import pytest

from neony.application import Config, NeonApplication


class FakeLumiApp:
    """Minimal lumiview App stand-in capturing hook registrations."""

    def __init__(self) -> None:
        self.hooks: dict = {}

    def on(self, event):
        def decorator(fn):
            self.hooks.setdefault(event, []).append(fn)
            return fn

        return decorator


def _wire(app: NeonApplication, fake: FakeLumiApp, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("neony.application.app.App.get", classmethod(lambda cls: fake))
    asyncio.run(app._wire_close_handler())


class TestShutdownHook:
    def test_close_handler_registered_and_fires(self, monkeypatch: pytest.MonkeyPatch):
        calls: list[str] = []
        app = NeonApplication(Config())
        app.close_handler = lambda: calls.append("shutdown")
        fake = FakeLumiApp()

        _wire(app, fake, monkeypatch)

        from lumiview._events import AppHookEvent

        handlers = fake.hooks.get(AppHookEvent.Close, [])
        assert len(handlers) == 1
        # Simulate lumiview emitting the Close event during shutdown.
        handlers[0]()
        assert calls == ["shutdown"]

    def test_no_handler_registers_nothing(self, monkeypatch: pytest.MonkeyPatch):
        app = NeonApplication(Config())
        fake = FakeLumiApp()

        _wire(app, fake, monkeypatch)

        assert fake.hooks == {}

    def test_async_close_handler_awaited(self, monkeypatch: pytest.MonkeyPatch):
        calls: list[str] = []
        app = NeonApplication(Config())

        async def handler() -> None:
            await asyncio.sleep(0)
            calls.append("async")

        app.close_handler = handler
        fake = FakeLumiApp()

        _wire(app, fake, monkeypatch)

        from lumiview._events import AppHookEvent

        asyncio.run(fake.hooks[AppHookEvent.Close][0]())
        assert calls == ["async"]
