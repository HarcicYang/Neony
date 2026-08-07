"""Window-level keyboard shortcut helpers (shared by Page and navigation
components).  Extracted from :mod:`neony.application.page` so that
:class:`Sidebar`-style components can validate and match shortcut combos
without importing Page (which imports the element library)."""

from __future__ import annotations

import sys

from neony.dom import DomEvent

# Shortcut modifier tokens → DomEvent modifier field names.
_MODIFIER_ATTRS = {"ctrl": "ctrl_key", "shift": "shift_key", "alt": "alt_key", "meta": "meta_key"}


def resolve_combo(combo: str | dict[str, str]) -> str:
    """Resolve a per-platform combo dict to the current platform's string,
    or pass a plain string through::

        resolve_combo("Ctrl+S")                          # "Ctrl+S"
        resolve_combo({"darwin": "Meta+S", "default": "Ctrl+S"})

    Raises ``ValueError`` when the dict has no entry for the current
    ``sys.platform`` and no ``"default"`` fallback.
    """
    if isinstance(combo, str):
        return combo
    if sys.platform in combo:
        return combo[sys.platform]
    if "default" in combo:
        return combo["default"]
    raise ValueError(f"shortcut: no entry for platform {sys.platform!r}; add a 'default' key to the combo dict")


def parse_combo(combo: str) -> tuple[set[str], str]:
    """Split ``"Ctrl+Shift+S"`` into (modifier set, key)."""
    parts = [p for p in combo.split("+") if p]
    if len(parts) < 2:
        raise ValueError(f"shortcut: {combo!r} must be MODIFIER+KEY, e.g. 'Ctrl+S'")
    modifiers: set[str] = set()
    for part in parts[:-1]:
        norm = part.lower()
        if norm not in _MODIFIER_ATTRS:
            raise ValueError(f"shortcut: unknown modifier {part!r} in {combo!r} (expected Ctrl / Shift / Alt / Meta)")
        modifiers.add(norm)
    return modifiers, parts[-1].lower()


def match_shortcut(evt: DomEvent, combo: str) -> bool:
    """True when *evt* (a keydown) exactly matches *combo*: all listed
    modifiers pressed, none extra, key equal case-insensitively."""
    if evt.type != "keydown" or evt.value is None:
        return False
    want_mods, want_key = parse_combo(combo)
    pressed = {m for m, attr in _MODIFIER_ATTRS.items() if getattr(evt, attr)}
    return pressed == want_mods and evt.value.lower() == want_key
