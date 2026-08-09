"""Typed CSS value models — colors, transitions, animation keyframes,
and the element ``Styles`` surface.

These are the building blocks every :class:`~neony.dom.base.DOMElement`
serializes into CSS text: ``Color`` / ``Transition`` / ``Animation``
appear as individual style values, ``Props`` + ``KeyFrame`` describe
``@keyframes`` rules, and ``Styles`` is the full style-surface model
attached to each element (with dirty-marking back to its owner).

Organised as a subpackage:
- ``_values`` — leaf CSS value models (``Color``; later phases add
  ``Length`` / ``Shadow`` / ``BoxShadow`` / ``Transform`` / ``Border`` / ``Filter``).
- ``_animation`` — ``Transition`` / ``Animation`` / ``Props`` /
  ``KeyFrame`` / ``KeyFrameStop``.
- ``_styles`` — the ``Styles`` aggregator.

All public names are re-exported here so ``from neony.dom.css import X``
keeps working whether ``X`` lives in ``_values`` or ``_styles``.
"""

from __future__ import annotations

from ._animation import Animation, KeyFrame, KeyFrameStop, Props, Transition
from ._styles import Styles
from ._values import BoxShadow, Color, Shadow

__all__ = [
    "Animation",
    "BoxShadow",
    "Color",
    "KeyFrame",
    "KeyFrameStop",
    "Props",
    "Shadow",
    "Styles",
    "Transition",
]
