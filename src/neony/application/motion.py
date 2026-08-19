"""Extensible motion tokens parallel to the semantic theme namespace.

Components reference the stub tokens rather than a concrete preset. A future
motion preset can change injected CSS variables without changing component code
or the public component API.
"""

from __future__ import annotations

from typing import ClassVar

from pydantic import BaseModel, ConfigDict

from neony.dom.css import Animation, Transition


class Motion(BaseModel):
    """Immutable motion preset registered by its name."""

    model_config = ConfigDict(frozen=True)
    _registry: ClassVar[dict[str, Motion]] = {}

    name: str
    fast: str
    normal: str
    slow: str
    ease_standard: str
    ease_enter: str
    ease_exit: str
    popup_animation: str
    submenu_animation: str

    def model_post_init(self, __context: object) -> None:
        type(self)._registry[self.name] = self

    @classmethod
    def get(cls, name: str) -> Motion:
        return cls._registry[name]

    @classmethod
    def names(cls) -> tuple[str, ...]:
        return tuple(cls._registry)

    def to_css(self) -> str:
        values = {
            "fast": self.fast,
            "normal": self.normal,
            "slow": self.slow,
            "ease-standard": self.ease_standard,
            "ease-enter": self.ease_enter,
            "ease-exit": self.ease_exit,
            "popup-animation": self.popup_animation,
            "submenu-animation": self.submenu_animation,
        }
        tokens = " ".join(f"--motion-{key}: {value};" for key, value in values.items())
        return f":root {{ {tokens} }}"


DEFAULT = Motion(
    name="default",
    fast="0.12s",
    normal="0.18s",
    slow="0.24s",
    ease_standard="ease",
    ease_enter="ease-out",
    ease_exit="ease-in",
    popup_animation="neony-drop-in",
    submenu_animation="neony-submenu-in",
)


class _MotionStub(Motion):
    """Typed token namespace backed by injected motion CSS variables."""

    def model_post_init(self, __context: object) -> None:
        pass

    name: str = "stub"
    fast: ClassVar[str] = "var(--motion-fast)"
    normal: ClassVar[str] = "var(--motion-normal)"
    slow: ClassVar[str] = "var(--motion-slow)"
    ease_standard: ClassVar[str] = "var(--motion-ease-standard)"
    ease_enter: ClassVar[str] = "var(--motion-ease-enter)"
    ease_exit: ClassVar[str] = "var(--motion-ease-exit)"
    popup_animation: ClassVar[str] = "var(--motion-popup-animation)"
    submenu_animation: ClassVar[str] = "var(--motion-submenu-animation)"


stub = _MotionStub()


def transition(*properties: str, duration: str | None = None, timing: str | None = None) -> Transition:
    """Build a transition using the active motion token namespace."""
    return Transition(
        property=", ".join(properties) if properties else "all",
        duration=duration or stub.normal,
        timing=timing or stub.ease_standard,
    )


def popup_animation() -> Animation:
    return Animation(name=DEFAULT.popup_animation, duration=stub.normal, timing=stub.ease_enter)


def submenu_animation() -> Animation:
    return Animation(name=DEFAULT.submenu_animation, duration=stub.normal, timing=stub.ease_enter)
