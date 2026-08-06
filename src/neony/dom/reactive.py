"""Fine-grained reactive primitives — Signal, Computed, Effect.

Signal holds a value and notifies subscribers on write; Computed derives
cached values with automatic dependency tracking; Effect runs a function
immediately and re-runs it whenever any Signal it read changes.

Dependency tracking is scope-based: while a node is evaluating, every
read is recorded as a dependency.  Re-runs are coalesced — deferred to
``loop.call_soon`` when a loop is running, synchronous otherwise, always
coalesced inside :func:`batch` (deferring while another effect runs also
prevents recursion when an effect writes a Signal it reads).

Usage::

    count = Signal(0)
    stop = effect(lambda: print(count()))
    count.set(1)  # re-runs, prints 1
    stop.dispose()
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Generator
from contextlib import contextmanager
from typing import Generic, TypeVar, cast

T = TypeVar("T")

_TRACKING: list[ReactiveNode] = []
_PENDING: set[Effect] = set()
_SCHEDULED = False
_BATCH_DEPTH = 0
_RUNNING_EFFECTS = 0


def _get_running_loop() -> asyncio.AbstractEventLoop | None:
    try:
        return asyncio.get_running_loop()
    except RuntimeError:
        return None


class Source:
    """Base for subscribable values (Signal, Computed).  Not generic —
    the type parameter lives on the leaf classes."""

    def __init__(self) -> None:
        self._subs: set[ReactiveNode] = set()

    def _notify(self) -> None:
        for sub in list(self._subs):
            sub._mark_dirty()


class ReactiveNode:
    """Base for dependency-tracking nodes (Effect, Computed)."""

    def __init__(self) -> None:
        self._deps: set[Source] = set()

    def _depends(self, source: Source) -> None:
        self._deps.add(source)
        source._subs.add(self)

    def _begin_track(self) -> None:
        # Drop stale subscriptions: an effect whose branch changed must
        # stop listening to abandoned sources.
        for dep in self._deps:
            dep._subs.discard(self)
        self._deps.clear()
        _TRACKING.append(self)

    def _end_track(self) -> None:
        _TRACKING.pop()

    def _mark_dirty(self) -> None:  # pragma: no cover - overridden
        raise NotImplementedError


class Signal(Source, Generic[T]):
    """A single reactive value.  Read with ``signal()`` (records a
    dependency inside an effect/computed); write with ``set()`` /
    ``update()``.  Writing an equal value (``==``) notifies nothing."""

    def __init__(self, value: T) -> None:
        super().__init__()
        self._value = value

    def get(self) -> T:
        top = _TRACKING[-1] if _TRACKING else None
        if top is not None:
            top._depends(self)
        return self._value

    def __call__(self) -> T:
        return self.get()

    def set(self, value: T) -> None:
        try:
            same = value == self._value
        except Exception:
            same = value is self._value
        if same:
            return
        self._value = value
        self._notify()

    def update(self, fn: Callable[[T], T]) -> None:
        """Mutate in place: ``self.set(fn(self.get()))``."""
        self.set(fn(self.get()))


class SharedSignal(Signal[T]):
    """A :class:`Signal` meant for cross-window state — behaviourally
    identical (objects are shared by reference); the intent stays
    explicit in multi-window apps."""


class Computed(Source, ReactiveNode, Generic[T]):
    """Lazily evaluated, cached derived value; recomputes only when a
    dependency changed.  Computeds may depend on other computeds."""

    def __init__(self, fn: Callable[[], T]) -> None:
        Source.__init__(self)
        ReactiveNode.__init__(self)
        self._fn = fn
        self._value: T | None = None
        self._computed = False
        self._dirty = True

    def get(self) -> T:
        top = _TRACKING[-1] if _TRACKING else None
        if top is not None:
            top._depends(self)
        if self._dirty or not self._computed:
            self._recompute()
        return cast(T, self._value)

    def __call__(self) -> T:
        return self.get()

    def _recompute(self) -> None:
        self._begin_track()
        try:
            self._value = self._fn()
            self._computed = True
        finally:
            self._end_track()
        self._dirty = False

    def _mark_dirty(self) -> None:
        self._dirty = True
        self._notify()


class Effect(ReactiveNode):
    """Run *fn* immediately, then re-run it when a dependency changes.
    ``dispose()`` unsubscribes from every dependency."""

    def __init__(self, fn: Callable[[], None]) -> None:
        super().__init__()
        self._fn = fn
        self._disposed = False
        self._run_now()

    def _run_now(self) -> None:
        global _RUNNING_EFFECTS
        if self._disposed:
            return
        self._begin_track()
        _RUNNING_EFFECTS += 1
        try:
            self._fn()
        finally:
            _RUNNING_EFFECTS -= 1
            self._end_track()
        # Flush effects queued by this run once we're back at top level.
        if _PENDING and _RUNNING_EFFECTS == 0 and _BATCH_DEPTH == 0 and _get_running_loop() is None:
            _flush()

    def _mark_dirty(self) -> None:
        if not self._disposed:
            _schedule(self)

    def dispose(self) -> None:
        """Stop the effect and unsubscribe from all dependencies."""
        self._disposed = True
        for dep in self._deps:
            dep._subs.discard(self)
        self._deps.clear()


def effect(fn: Callable[[], None]) -> Effect:
    """Create and run an :class:`Effect` immediately (see its docstring)."""
    return Effect(fn)


def untrack(fn: Callable[[], T]) -> T:
    """Run *fn* without recording any dependency reads."""
    saved = list(_TRACKING)
    _TRACKING.clear()  # in-place: rebinding the module name would make it local
    try:
        return fn()
    finally:
        _TRACKING[:] = saved


def _schedule(eff: Effect) -> None:
    if eff._disposed or eff in _PENDING:
        return
    if _BATCH_DEPTH > 0:
        _PENDING.add(eff)
        return
    loop = _get_running_loop()
    if loop is not None:
        global _SCHEDULED
        _PENDING.add(eff)
        if not _SCHEDULED:
            _SCHEDULED = True
            loop.call_soon(_flush)
        return
    if _RUNNING_EFFECTS > 0:
        # Defer to the tail flush — running now would recurse the writer's stack.
        _PENDING.add(eff)
        return
    eff._run_now()


def _flush() -> None:
    global _SCHEDULED
    _SCHEDULED = False
    pending = list(_PENDING)
    _PENDING.clear()
    for eff in pending:
        if eff._disposed:
            continue
        try:
            eff._run_now()
        except Exception:
            # One crash must not block the batch (the tracking stack is
            # restored via finally, so only this run is lost).
            import logging

            logging.getLogger("neony.reactive").exception("Effect crashed")
            continue


@contextmanager
def batch() -> Generator[None]:
    """Coalesce writes: effects queued inside the block run once on exit.

    Works with or without a running event loop.
    """
    global _BATCH_DEPTH
    _BATCH_DEPTH += 1
    try:
        yield
    finally:
        _BATCH_DEPTH -= 1
        if _BATCH_DEPTH == 0:
            _flush()
