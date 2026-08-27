"""A RollingSlicer pass must take `pass_seconds`, whatever rate the host calls it at.

WHAT WAS WRONG. `slice()` added `n / (pass_seconds * tps)` once PER CALL, which delivers
the advertised period only if the host calls it exactly `tps` (30) times a sim-second.
Measured 2026-08-26, both hosts running time_tick_counter at 30.0/sim-second:

    engine 1.3.7   15.0 dispatch calls/sim-second  -> a pass took 2x as long as declared
    mock             6.0 calls/sim-second          -> 5x as long

So `BRAIN_PASS_SECONDS = 3` meant a 6-second pass in the engine and a 15-second one
headless, and the two hosts disagreed with each other by 2.5x. Nothing reported it: a
slow brain looks exactly like a brain whose leaves declined.

The symptom that led here was a brain-driven player ship that almost never warped, while
the same logic written as a `delay_sim(1)` loop warped four times as often -- it simply
re-decided its throttle every ~15 seconds instead of every 3, so it never sampled the
middle of the speed ladder while closing on a target.

These tests drive the slicer at several call rates against a fake clock. Under the old
per-call code the 30/second case passes and every other case is off by exactly the rate
ratio, which is the regression to hold.
"""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

from sbs_utils.tickdispatcher import RollingSlicer, TickDispatcher


class FakeClock:
    """Stands in for `FrameContext.context.sim.time_tick_counter`."""

    def __init__(self):
        self.ticks = 0


class RollingSlicerCadenceTests(unittest.TestCase):
    def setUp(self):
        self.clock = FakeClock()
        self._real_now = RollingSlicer._now_tick
        RollingSlicer._now_tick = staticmethod(lambda: self.clock.ticks)

    def tearDown(self):
        RollingSlicer._now_tick = self._real_now

    def _run(self, n_items, pass_seconds, calls_per_second, sim_seconds):
        """Drive a slicer for `sim_seconds` at a given call rate; count items handed out."""
        slicer = RollingSlicer()
        ids = set(range(n_items))
        ticks_per_call = TickDispatcher.tps / calls_per_second
        handed = 0
        total_calls = int(calls_per_second * sim_seconds)
        for i in range(total_calls):
            self.clock.ticks = int(round((i + 1) * ticks_per_call))
            handed += len(slicer.slice(ids, pass_seconds))
        return handed

    def test_pass_period_holds_at_the_engines_real_rate(self):
        """15 calls/sim-second, the measured engine rate. Was 2x too slow."""
        # 60 sim-seconds / 3-second pass = 20 passes over 10 items = ~200 items.
        handed = self._run(10, pass_seconds=3, calls_per_second=15, sim_seconds=60)
        self.assertAlmostEqual(handed / 10.0, 20, delta=1,
                               msg="a 3-second pass must complete 20 times in 60 seconds")

    def test_pass_period_holds_at_the_mocks_real_rate(self):
        """6 calls/sim-second, the measured mock rate. Was 5x too slow."""
        handed = self._run(10, pass_seconds=3, calls_per_second=6, sim_seconds=60)
        self.assertAlmostEqual(handed / 10.0, 20, delta=1,
                               msg="the headless host must get the same cadence as the engine")

    def test_the_two_hosts_now_agree(self):
        """The divergence itself, stated as a test: same work, same period, both rates."""
        engine = self._run(10, pass_seconds=3, calls_per_second=15, sim_seconds=60)
        mock = self._run(10, pass_seconds=3, calls_per_second=6, sim_seconds=60)
        self.assertAlmostEqual(engine, mock, delta=12,
                               msg=f"engine handed {engine}, mock handed {mock}")

    def test_still_correct_at_the_rate_it_always_assumed(self):
        """30 calls/second was the one rate the old code got right. Keep it right."""
        handed = self._run(10, pass_seconds=3, calls_per_second=30, sim_seconds=60)
        self.assertAlmostEqual(handed / 10.0, 20, delta=1)

    def test_it_is_still_sliced_not_batched(self):
        """The anti-spike property must survive: no call may hand out the whole set."""
        slicer = RollingSlicer()
        ids = set(range(100))
        worst = 0
        for i in range(300):
            self.clock.ticks = i * 2          # 15 calls/sim-second
            worst = max(worst, len(slicer.slice(ids, 3)))
        self.assertLess(worst, 100, "a single call handed out the entire set")

    def test_an_idle_stretch_does_not_bank_time(self):
        """A long gap must not spend itself in one batch when work reappears.

        This is why elapsed time is consumed before the empty-set return, and why it is
        clamped to one pass. Without both, a set that sits empty for a minute hands its
        whole membership back on the first call after it fills - the exact spike the
        class exists to prevent.
        """
        slicer = RollingSlicer()
        for i in range(30):                    # a minute of nothing to do
            self.clock.ticks = i * 60
            slicer.slice(set(), 3)
        self.clock.ticks += 60
        first = len(slicer.slice(set(range(100)), 3))
        self.assertLess(first, 100, f"handed {first}/100 items in the first call after idle")

    def test_a_restarted_tick_counter_does_not_stall_it(self):
        """A new mission restarts the counter; a negative jump is not elapsed time."""
        slicer = RollingSlicer()
        ids = set(range(10))
        self.clock.ticks = 100000
        for _ in range(5):
            self.clock.ticks += 2
            slicer.slice(ids, 3)
        self.clock.ticks = 0                   # mission restart
        slicer.slice(ids, 3)                   # must not bank a huge negative
        handed = 0
        for i in range(150):                   # 10 sim-seconds at 15/second
            self.clock.ticks = i * 2
            handed += len(slicer.slice(ids, 3))
        self.assertGreater(handed, 20, "the slicer stalled after a counter restart")

    def test_it_works_with_no_sim_at_all(self):
        """No FrameContext (a plain unit test) must not raise - it falls back to counting."""
        RollingSlicer._now_tick = staticmethod(lambda: None)
        slicer = RollingSlicer()
        handed = sum(len(slicer.slice(set(range(10)), 3)) for _ in range(300))
        self.assertGreater(handed, 0)


if __name__ == "__main__":
    unittest.main()
