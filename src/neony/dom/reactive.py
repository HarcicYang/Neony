"""Fine-grained reactive primitives — Signal, Computed, Effect.

The V-DOM diff engine reacts to whole-tree mutations; these primitives
react to individual state changes.  A :class:`Signal` holds a value and
notifies subscribers on write; :class:`Computed` derives values with
automatic dependency tracking and caching; :class:`Effect` runs a
function immediately and re-runs it whenever any Signal it read changes.

Dependency tracking is scope-based: while a node (Effect or Computed) is
evaluating, every Signal/Computed read is recorded as a dependency.
Writes notify subscribers; Effects re-run (batch-coalesced), Computeds
mark themselves dirty and invalidate their own subscribers.

Usage::

    count = Signal(0)
    double = Computed(lambda: count() * 2)

    def log():
        print("count is", count())
    stop = effect(log)          # runs immediately: prints 0

    count.set(1)                # log re-runs: prints 1

    with batch():
        count.set(2)
        count.set(3)            # one re-run, not two
    stop.dispose()              # no more re-runs

Scheduling: with a running asyncio loop, effect re-runs are deferred to
``loop.call_soon`` — multiple writes in one synchronous block coalesce
into a single re-run (the microtask coalescing).  Without a loop, re-runs
are synchronous, except inside :func:`batch` (always coalesced) or while
another effect is running (deferred until it finishes, which prevents
infinite recursion when an effect writes a Signal it reads).
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Iterator
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
    """Base for things that can be subscribed to (Signal, Computed).

    Not generic: the type parameter lives on the leaf classes (Signal[T],
    Computed[T]).  No ``__slots__`` — the primitives are few (user-level
    state), the gain is negligible, and slots complicate Computed's
    multiple inheritance and pyrefly's attribute checking.
    """

    def __init__(self) -> None:
        self._subs: set[ReactiveNode] = set()

    def _notify(self) -> None:
        for sub in list(self._subs):
            sub._mark_dirty()


class ReactiveNode:
    """Base for things that track dependencies (Effect, Computed).

    While a node is evaluating, every Source read is recorded in
    ``_deps`` and subscribes the node to that source.
    """

    def __init__(self) -> None:
        self._deps: set[Source] = set()

    def _depends(self, source: Source) -> None:
        self._deps.add(source)
        source._subs.add(self)

    def _begin_track(self) -> None:
        # Drop stale subscriptions before re-collecting: an effect whose
        # branch changed must stop listening to abandoned sources.
        for dep in self._deps:
            dep._subs.discard(self)
        self._deps.clear()
        _TRACKING.append(self)

    def _end_track(self) -> None:
        _TRACKING.pop()

    def _mark_dirty(self) -> None:  # pragma: no cover - overridden
        raise NotImplementedError


class Signal(Source, Generic[T]):
    """A single reactive value.

    Read with ``signal()`` or ``signal.get()`` (inside an effect/computed
    this records a dependency); write with ``signal.set(value)`` or
    ``signal.update(fn)``.  Writing an equal value (``==``) notifies
    nothing.
    """

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
    """A :class:`Signal` meant to be shared across every window.

    Behaviourally identical to ``Signal`` — Python objects are shared by
    reference, and bindings in every window's tree subscribe to the same
    signal, so a write updates all windows (each window schedules its own
    render through its tree root).  Declaring the intent explicitly keeps
    multi-window apps readable.
    """


class Computed(Source, ReactiveNode, Generic[T]):
    """A lazily evaluated, cached derived value.

    ``computed()`` returns the cached value, recomputing only when a
    dependency changed.  Computeds may depend on other computeds and
    are themselves valid dependencies for effects and other computeds.
    """

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

    Disposable: ``effect.dispose()`` unsubscribes from every dependency
    so the effect (and anything it captured) can be garbage collected.
    """

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
        # A write inside the effect may have queued other effects in the
        # no-loop path — flush them once we're back at the top level.
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
        # Defer to the effect's tail flush — running it now would recurse
        # into the writer's stack.
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
            # One crashing effect must not block the rest of the batch.
            # (Effect._run_now guarantees the tracking stack is restored
            # via finally, so the crash only loses this effect's run.)
            import logging

            logging.getLogger("neony.reactive").exception("Effect crashed")
            continue


@contextmanager
def batch() -> Iterator[None]:
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
