#!/usr/bin/env python3
"""Small, dependency-light performance probes for Neony hot paths.

This is intentionally separate from pytest: run it directly to compare a
checkout against a local baseline without making timing assertions in CI.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import time
from collections.abc import Awaitable, Callable
from typing import Any

from neony.application.elements import Column, DataTable, List
from neony.dom import Div, Span, Styles
from neony.dom.bridge import Neony


def _tree(size: int) -> Div:
    return Div(key="root", container=[Span(key=f"n{i}", container=[str(i)]) for i in range(size)])


def _summary(samples: list[float]) -> dict[str, float | int]:
    ordered = sorted(samples)
    return {
        "repeats": len(samples),
        "median_ms": statistics.median(samples),
        "p95_ms": ordered[min(len(ordered) - 1, int(len(ordered) * 0.95))],
        "min_ms": min(samples),
        "max_ms": max(samples),
    }


def _measure(fn: Callable[[], Any], repeats: int) -> dict[str, float | int]:
    samples: list[float] = []
    for _ in range(repeats):
        start = time.perf_counter_ns()
        fn()
        samples.append((time.perf_counter_ns() - start) / 1_000_000)
    return _summary(samples)


async def _measure_async(fn: Callable[[], Awaitable[Any]], repeats: int) -> dict[str, float | int]:
    samples: list[float] = []
    for _ in range(repeats):
        start = time.perf_counter_ns()
        await fn()
        samples.append((time.perf_counter_ns() - start) / 1_000_000)
    return _summary(samples)


class _Window:
    def __init__(self) -> None:
        self.patches: list[dict[str, Any]] = []

    async def emit(self, event: str, payload: dict[str, Any]) -> None:
        assert event == "neony:patch"
        self.patches.append(payload)

    async def eval_js(self, script: str) -> str:
        return '{"ok": true}'


async def _bridge_probe(size: int, repeats: int) -> tuple[dict[str, float | int], dict[str, int]]:
    root = _tree(size)
    leaf = root.container[-1]
    assert isinstance(leaf, Span)
    bridge = Neony(name="benchmark", mount_selector="body")
    window = _Window()
    bridge._win = window  # type: ignore[assignment]
    await bridge.render(root)
    window.patches.clear()
    state = False

    async def update() -> None:
        nonlocal state
        state = not state
        leaf.styles = Styles(opacity=0.5 if state else 1.0)
        await bridge.render(root)

    timing = await _measure_async(update, repeats)
    payload_bytes = sum(len(json.dumps(patch, separators=(",", ":"))) for patch in window.patches)
    return timing, {
        "snapshot_count": len(bridge._snapshots),
        "patch_messages": len(window.patches),
        "payload_bytes": payload_bytes,
    }


async def run(size: int, repeats: int) -> dict[str, Any]:
    first = _measure(lambda: _tree(size).to_node({}), repeats)

    root = _tree(size)
    cache: dict[str, Any] = {}
    root.to_node(cache)
    leaf = root.container[-1]
    assert isinstance(leaf, Span)
    text_state = False

    def mutate_and_serialize() -> None:
        nonlocal text_state
        text_state = not text_state
        leaf.container = ["changed" if text_state else "original"]
        root.to_node(cache)

    dirty = _measure(mutate_and_serialize, repeats)
    direct, bridge_metrics = await _bridge_probe(size, repeats)

    rows = [{"name": f"row-{i}", "value": i} for i in range(size)]
    table = DataTable(columns=[Column("Name"), Column("Value")], rows=rows, row_key=lambda row: row["name"])
    table_keys = iter([f"row-{size // 2}", f"row-{size // 2 + 1}"] * repeats)
    table_select = _measure(lambda: setattr(table, "selected_key", next(table_keys)), repeats)

    listing = List(*(f"row-{i}" for i in range(size)))
    list_keys = iter([f"row-{size // 2}", f"row-{size // 2 + 1}"] * repeats)
    list_select = _measure(lambda: setattr(listing, "selected_key", next(list_keys)), repeats)
    return {
        "size": size,
        "tree": {"first_render": first, "dirty_leaf": dirty, "bridge_direct_style": direct},
        "selection": {"list": list_select, "datatable": table_select},
        "metrics": {
            **bridge_metrics,
            "list_logical_items": len(listing.items),
            "list_materialized_rows": len(listing._row_by_key),
        },
    }


async def _main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--sizes", nargs="+", type=int, default=[100, 1000, 10000])
    parser.add_argument("--repeats", type=int, default=15)
    parser.add_argument("--json", action="store_true", help="emit JSON only")
    args = parser.parse_args()
    result = {"benchmarks": [await run(size, args.repeats) for size in args.sizes]}
    print(json.dumps(result, indent=None if args.json else 2, sort_keys=True))


if __name__ == "__main__":
    asyncio.run(_main())
