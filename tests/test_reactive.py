"""Tests for the reactive primitives — Signal, Computed, Effect, batch."""

import asyncio

from neony.dom.reactive import Computed, Signal, batch, effect, untrack


class TestSignal:
    def test_get_set_call(self):
        s = Signal(0)
        assert s.get() == 0
        assert s() == 0
        s.set(5)
        assert s() == 5

    def test_update(self):
        s = Signal(0)
        s.update(lambda v: v + 1)
        assert s() == 1

    def test_equal_write_does_not_notify(self):
        s = Signal(1)
        hits = []
        effect(lambda: hits.append(s()))
        s.set(1)  # equal — must not re-run
        assert len(hits) == 1

    def test_typed_value(self):
        s = Signal("hello")
        s.set("world")
        assert s() == "world"


class TestComputed:
    def test_lazy_and_cached(self):
        calls = []
        s = Signal(1)
        c = Computed(lambda: calls.append(s()) or s() * 2)
        assert calls == []  # lazy: nothing evaluated yet
        assert c() == 2
        assert c() == 2  # cached: no recompute
        assert len(calls) == 1

    def test_recomputes_on_dependency_change(self):
        s = Signal(1)
        c = Computed(lambda: s() * 2)
        assert c() == 2
        s.set(5)
        assert c() == 10
        assert c() == 10  # cached again

    def test_computed_of_computed(self):
        a = Signal(2)
        b = Computed(lambda: a() * 2)
        c = Computed(lambda: b() + 1)
        assert c() == 5
        a.set(4)
        assert c() == 9

    def test_effect_reacts_to_computed_chain(self):
        a = Signal(1)
        b = Computed(lambda: a() * 10)
        hits = []
        effect(lambda: hits.append(b()))
        assert hits == [10]
        a.set(2)
        assert hits == [10, 20]


class TestEffect:
    def test_runs_immediately(self):
        hits = []
        effect(lambda: hits.append(1))
        assert hits == [1]

    def test_reruns_on_dependency_change(self):
        s = Signal(0)
        hits = []
        effect(lambda: hits.append(s()))
        s.set(1)
        s.set(2)
        assert hits == [0, 1, 2]

    def test_multiple_dependencies(self):
        a = Signal(1)
        b = Signal(2)
        hits = []
        effect(lambda: hits.append(a() + b()))
        assert hits == [3]
        a.set(10)
        assert hits == [3, 12]
        b.set(20)
        assert hits == [3, 12, 30]

    def test_dropped_dependency_stops_triggering(self):
        """An effect that stops reading a signal must unsubscribe from it."""
        flag = Signal(True)
        s = Signal(0)
        hits: list[object] = []

        def fn():
            if flag():
                hits.append(s())
            else:
                hits.append("skip")

        effect(fn)
        # initial run: flag True → reads s → both are deps
        assert hits == [0]
        flag.set(False)  # effect re-runs, now only reads flag
        assert hits == [0, "skip"]
        s.set(99)  # must NOT trigger — s is no longer a dependency
        assert hits == [0, "skip"]
        flag.set(True)  # re-reads s
        assert hits == [0, "skip", 99]

    def test_dispose_stops_reruns(self):
        s = Signal(0)
        hits = []
        eff = effect(lambda: hits.append(s()))
        assert hits == [0]
        eff.dispose()
        s.set(1)
        s.set(2)
        assert hits == [0]
        assert s._subs == set()  # unsubscribed from the signal


class TestBatch:
    def test_batch_coalesces_without_loop(self):
        s = Signal(0)
        hits = []
        effect(lambda: hits.append(s()))
        assert hits == [0]
        with batch():
            s.set(1)
            s.set(2)
            assert hits == [0]  # nothing yet — coalesced
        assert hits == [0, 2]  # exactly one re-run, with the final value

    def test_nested_batch_flushes_once(self):
        s = Signal(0)
        hits = []
        effect(lambda: hits.append(s()))
        with batch():
            s.set(1)
            with batch():
                s.set(2)
                s.set(3)
        assert hits == [0, 3]

    def test_batch_coalesces_across_effects(self):
        a = Signal(0)
        b = Signal(0)
        hits = []
        effect(lambda: hits.append(a() + b()))
        with batch():
            a.set(1)
            b.set(2)
        assert hits == [0, 3]


class TestAsyncScheduling:
    def test_loop_call_soon_coalesces(self):
        """With a running loop, writes in one synchronous block coalesce
        into a single re-run on the next loop iteration."""

        async def run():
            s = Signal(0)
            hits = []
            effect(lambda: hits.append(s()))
            s.set(1)
            s.set(2)
            s.set(3)
            assert hits == [0]  # deferred — not yet flushed
            await asyncio.sleep(0)  # let call_soon fire
            return hits

        hits = asyncio.run(run())
        assert hits == [0, 3]

    def test_effect_writing_signal_does_not_recursively_reenter(self):
        """An effect that writes a signal it reads must not recurse
        infinitely — the re-run is deferred."""

        async def run():
            s = Signal(0)
            hits = []

            def fn():
                hits.append(s())
                if s() < 3:
                    s.set(s() + 1)

            effect(fn)
            await asyncio.sleep(0)
            await asyncio.sleep(0)
            await asyncio.sleep(0)
            return hits

        hits = asyncio.run(run())
        assert hits == [0, 1, 2, 3]  # each set schedules exactly one re-run

    def test_no_loop_effect_self_write_deferred_to_tail(self):
        """Same protection without a loop: the re-run is deferred until
        the current effect finishes, then flushed synchronously."""

        def run():
            s = Signal(0)
            hits = []

            def fn():
                hits.append(s())
                if s() < 3:
                    s.set(s() + 1)

            effect(fn)
            return hits

        hits = run()
        assert hits == [0, 1, 2, 3]


class TestUntrack:
    def test_untracked_read_creates_no_dependency(self):
        s = Signal(1)
        hits = []
        effect(lambda: hits.append(untrack(s.get)))
        assert hits == [1]
        s.set(2)
        assert hits == [1]  # read was untracked → no dependency → no re-run

    def test_untrack_restores_tracking(self):
        s = Signal(1)
        hits = []

        def fn():
            hits.append(untrack(s.get))  # not tracked, but reads the current value
            hits.append(s())  # tracked — keeps s a dependency

        effect(fn)
        assert hits == [1, 1]
        s.set(2)
        # the untracked read still sees the new value — it just doesn't
        # establish a dependency; the re-run happened because of s()
        assert hits == [1, 1, 2, 2]

    def test_untrack_returns_value(self):
        s = Signal(5)
        assert untrack(lambda: s() + 1) == 6

    def test_effect_can_write_untracked_counter(self):
        trigger = Signal(0)
        runs = Signal(0)

        def sync() -> None:
            trigger()
            runs.update(lambda value: value + 1)

        effect(sync)
        assert runs() == 1
        trigger.set(1)
        assert runs() == 2

    def test_effect_creating_effect(self):
        """Nested effects track their own dependencies independently.

        The inner effect is created once, during the outer's first run —
        creating it inside the lambda on every run would duplicate it.
        """
        s = Signal(0)
        outer = []
        inner = []
        inner_effects = []

        def build():
            outer.append(s())
            if not inner_effects:
                inner_effects.append(effect(lambda: inner.append(s() * 10)))

        effect(build)
        assert outer == [0]
        assert inner == [0]  # inner ran once at creation
        s.set(1)
        assert outer == [0, 1]
        assert inner == [0, 10]  # the one inner effect re-ran
        assert len(inner_effects) == 1  # not duplicated by outer re-runs


class TestNoDependencies:
    def test_effect_without_dependencies_runs_once(self):
        hits = []
        eff = effect(lambda: hits.append("x"))
        assert hits == ["x"]
        eff.dispose()
        assert hits == ["x"]
