"""The JSON-safe node snapshot the diff engine works on."""

from __future__ import annotations

from pydantic import BaseModel
from pydantic.fields import Field


class NodeDescriptor(BaseModel):
    """JSON-safe snapshot of one DOM element — the serialized shape the
    bridge diffs and sends to the JavaScript engine."""

    key: str
    tag: str
    attrs: dict[str, str] = Field(default_factory=dict)
    styles: dict[str, str] = Field(default_factory=dict)
    text: str | None = None
    children: list[NodeDescriptor] = Field(default_factory=list)
