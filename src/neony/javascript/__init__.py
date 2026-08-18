"""Neony JavaScript runtime — loaded and injected into every LumiView page.

The JS source files are concatenated in dependency order
(builder → engine → index → editor) and exposed as :data:`ENGINE_SOURCE`.
"""

from pathlib import Path

_JS_FILES = ("builder.js", "engine.js", "index.js", "editor.js")
_DIR = Path(__file__).resolve().parent


def _load() -> str:
    """Read and concatenate JS source files in dependency order."""
    parts: list[str] = []
    for name in _JS_FILES:
        raw = (_DIR / name).read_text(encoding="utf-8")
        parts.append(raw)
    return "\n".join(parts)


ENGINE_SOURCE: str = _load()

__all__ = ["ENGINE_SOURCE"]
