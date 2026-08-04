"""Dedicated tests for the Effect system.

Phase 1 covered the basics (immediate run, dependency re-runs, dispose,
batch coalescing — see test_reactive.py).  These cover the harder
properties: crash isolation, system consistency after a crash, and
lifecycle behaviour.
"""

import asyncio

from neony.dom.reactive import Computed, Signal, batch, effect, untrack


class TestCrashIsolation:
    def test_crashing_effect_does_not_block_other_effects(self):
        s = Signal(0)
        bad_hits: list[int] = []
        good_hits: list[int] = []

        def bad():
            bad_hits.append(s())
            if s() >= 1:
                raise RuntimeError("boom")

        def good():
            good_hits.append(s())

        effect(bad)
        effect(good)
        assert good_hits == [0]

        # batch-flushed: bad crashes on re-run, good must still re-run
        with batch():
            s.set(1)
        assert good_hits == [0, 1]

    def test_crash_does_not_corrupt_tracking_stack(self):
        """After a crashing effect, a new effect must still track
        dependencies normally (the tracking stack was restored)."""
        s = Signal(0)
        hits = []

        def bad():
            if s() >= 1:
                raise RuntimeError("boom")

        effect(bad)  # first run is fine (s == 0)
        effect(lambda: hits.append(s()))
        with batch():
            s.set(1)  # bad crashes inside the flush — isolated
        with batch():
            s.set(2)
        assert hits == [0, 1, 2]  # the new effect kept tracking through it

    def test_crashing_effect_recovers_on_next_write(self):
        """The crashed effect is re-scheduled by its (already collected)
        dependency — the crash only loses the run itself."""
        s = Signal(0)
        hits: list[str] = []

        def fn():
            hits.append("run")
            if s() == 1:
                raise RuntimeError("boom")

        effect(fn)
        with batch():
            s.set(1)
        assert hits == ["run", "run"]  # crashed on the 2nd run
        with batch():
            s.set(2)
        assert hits == ["run", "run", "run"]  # re-scheduled by s again

    def test_crash_in_batch_does_not_abort_flush(self):
        a = Signal(0)
        b = Signal(0)
        hits = []

        def bad():
            if a():
                raise RuntimeError("boom")

        def good():
            hits.append(b())

        effect(bad)
        effect(good)
        with batch():
            a.set(1)
            b.set(1)
        assert hits == [0, 1]  # good ran despite bad crashing


class TestSystemConsistencyAfterCrash:
    def test_signal_writes_still_work_after_crash(self):
        s = Signal(0)

        def bad():
            if s() >= 1:
                raise RuntimeError("boom")

        effect(bad)  # first run fine
        # the crashing effect does not swallow the write itself
        with batch():
            s.set(1)
        assert s() == 1

    def test_computed_still_correct_after_effect_crash(self):
        s = Signal(1)
        c = Computed(lambda: s() * 2)

        def bad():
            if s() >= 3:
                c()
                raise RuntimeError("boom")

        effect(bad)
        with batch():
            s.set(3)
        assert c() == 6


class TestLifecycle:
    def test_dispose_then_crash_is_noop(self):
        s = Signal(0)
        hits = []
        eff = effect(lambda: hits.append(s()))
        eff.dispose()
        assert hits == [0]
        s.set(1)
        assert hits == [0]

    def test_disposed_effect_not_rerun_by_flush(self):
        s = Signal(0)
        hits = []
        with batch():
            eff = effect(lambda: hits.append(s()))
            eff.dispose()
            s.set(1)
        assert hits == [0]  # queued-but-disposed → skipped in flush

    def test_untrack_isolates_effect_from_dependencies(self):
        s = Signal(0)
        hits: list[object] = []

        def fn():
            untrack(lambda: hits.append("untracked"))
            hits.append(s())

        effect(fn)
        s.set(1)
        assert hits == ["untracked", 0, "untracked", 1]


class TestAsyncEffect:
    def test_async_flush_runs_all_pending(self):
        """With a running loop, one flush processes every pending effect
        from the same synchronous block (coalesced via call_soon)."""

        async def run():
            a = Signal(0)
            b = Signal(0)
            hits = []
            effect(lambda: hits.append(("a", a())))
            effect(lambda: hits.append(("b", b())))
            a.set(1)
            b.set(1)
            b.set(2)
            await asyncio.sleep(0)
            return hits

        hits = asyncio.run(run())
        # _PENDING is a set — flush order is unspecified, compare as a multiset
        assert sorted(hits) == [("a", 0), ("a", 1), ("b", 0), ("b", 2)]

    def test_crash_in_async_flush_does_not_block_others(self):
        async def run():
            s = Signal(0)
            good_hits = []

            def bad():
                if s():
                    raise RuntimeError("boom")

            def good():
                good_hits.append(s())

            effect(bad)
            effect(good)
            s.set(1)
            s.set(2)
            await asyncio.sleep(0)
            return good_hits

        good_hits = asyncio.run(run())
        assert good_hits == [0, 2]  # good survived the crashed batch
