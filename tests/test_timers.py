from cosmos_dev.mock import sbs as sbs
from sbs_utils.spaceobject import SpaceObject
from sbs_utils.agent import Agent, get_story_id
from sbs_utils.helpers import FrameContext, Context, FakeEvent
from sbs_utils.fs import test_set_exe_dir
from sbs_utils.procedural.timers import (
    set_timer, is_timer_set, is_timer_finished, is_timer_set_and_finished,
    clear_timer, get_time_remaining, format_time_remaining, timer_add_time,
    start_counter, get_counter_elapsed_seconds, clear_counter,
    set_interval, clear_interval,
    timer_signals_clear, timer_signals_count, _signals_tick,
    TICK_PER_SECONDS,
)
from sbs_utils.tickdispatcher import TickDispatcher
from sbs_utils.gui import GuiClient
from sbs_utils.procedural.inventory import get_inventory_value
from sbs_utils.procedural.signal import signal_observe, signal_unobserve
import unittest

test_set_exe_dir()


def make_agent():
    a = Agent()
    a.id = get_story_id()
    a.add()
    return a


def advance_sim(seconds):
    """Advance the mock sim clock by N seconds."""
    sbs.sim._time_tick_counter += seconds * TICK_PER_SECONDS


class TestTimers(unittest.TestCase):

    def setUp(self):
        SpaceObject.clear()
        sbs.create_new_sim()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent())

    # ------------------------------------------------------------------
    # is_timer_set
    # ------------------------------------------------------------------

    def test_timer_not_set_initially(self):
        agent = make_agent()
        self.assertFalse(is_timer_set(agent.id, "attack"))

    def test_set_timer_marks_as_set(self):
        agent = make_agent()
        set_timer(agent.id, "attack", seconds=5)
        self.assertTrue(is_timer_set(agent.id, "attack"))

    def test_clear_timer_unsets(self):
        agent = make_agent()
        set_timer(agent.id, "attack", seconds=5)
        clear_timer(agent.id, "attack")
        self.assertFalse(is_timer_set(agent.id, "attack"))

    # ------------------------------------------------------------------
    # is_timer_finished
    # ------------------------------------------------------------------

    def test_unset_timer_counts_as_finished(self):
        agent = make_agent()
        self.assertTrue(is_timer_finished(agent.id, "never_set"))

    def test_timer_not_finished_immediately(self):
        agent = make_agent()
        set_timer(agent.id, "attack", seconds=5)
        self.assertFalse(is_timer_finished(agent.id, "attack"))

    def test_timer_finished_after_duration(self):
        agent = make_agent()
        set_timer(agent.id, "attack", seconds=5)
        advance_sim(6)
        self.assertTrue(is_timer_finished(agent.id, "attack"))

    def test_timer_not_finished_before_duration(self):
        agent = make_agent()
        set_timer(agent.id, "attack", seconds=10)
        advance_sim(5)
        self.assertFalse(is_timer_finished(agent.id, "attack"))

    def test_timer_with_minutes(self):
        agent = make_agent()
        set_timer(agent.id, "warp", minutes=1)
        advance_sim(59)
        self.assertFalse(is_timer_finished(agent.id, "warp"))
        advance_sim(2)
        self.assertTrue(is_timer_finished(agent.id, "warp"))

    def test_timer_seconds_and_minutes_combined(self):
        agent = make_agent()
        set_timer(agent.id, "mission", minutes=1, seconds=30)
        advance_sim(89)
        self.assertFalse(is_timer_finished(agent.id, "mission"))
        advance_sim(2)
        self.assertTrue(is_timer_finished(agent.id, "mission"))

    # ------------------------------------------------------------------
    # is_timer_set_and_finished
    # ------------------------------------------------------------------

    def test_set_and_finished_false_when_not_set(self):
        agent = make_agent()
        self.assertFalse(is_timer_set_and_finished(agent.id, "attack"))

    def test_set_and_finished_false_before_time(self):
        agent = make_agent()
        set_timer(agent.id, "attack", seconds=5)
        self.assertFalse(is_timer_set_and_finished(agent.id, "attack"))

    def test_set_and_finished_true_after_time(self):
        agent = make_agent()
        set_timer(agent.id, "attack", seconds=5)
        advance_sim(6)
        self.assertTrue(is_timer_set_and_finished(agent.id, "attack"))

    # ------------------------------------------------------------------
    # get_time_remaining / format_time_remaining
    # ------------------------------------------------------------------

    def test_get_time_remaining(self):
        agent = make_agent()
        set_timer(agent.id, "cooldown", seconds=10)
        advance_sim(3)
        self.assertEqual(get_time_remaining(agent.id, "cooldown"), 7)

    def test_get_time_remaining_unset_returns_zero(self):
        agent = make_agent()
        self.assertEqual(get_time_remaining(agent.id, "nothing"), 0)

    def test_format_time_remaining_mm_ss(self):
        agent = make_agent()
        set_timer(agent.id, "mission", minutes=1, seconds=5)
        advance_sim(5)
        self.assertEqual(format_time_remaining(agent.id, "mission"), "1:00")

    def test_format_time_remaining_seconds_only(self):
        agent = make_agent()
        set_timer(agent.id, "reload", seconds=45)
        self.assertEqual(format_time_remaining(agent.id, "reload"), "0:45")

    def test_format_time_remaining_expired_is_empty(self):
        agent = make_agent()
        set_timer(agent.id, "attack", seconds=5)
        advance_sim(10)
        self.assertEqual(format_time_remaining(agent.id, "attack"), "")

    # ------------------------------------------------------------------
    # Multiple timers / agents stay independent
    # ------------------------------------------------------------------

    def test_multiple_timers_on_same_agent(self):
        agent = make_agent()
        set_timer(agent.id, "fast", seconds=2)
        set_timer(agent.id, "slow", seconds=10)
        advance_sim(3)
        self.assertTrue(is_timer_finished(agent.id, "fast"))
        self.assertFalse(is_timer_finished(agent.id, "slow"))

    def test_timer_on_one_agent_does_not_affect_another(self):
        a1 = make_agent()
        a2 = make_agent()
        set_timer(a1.id, "attack", seconds=5)
        self.assertFalse(is_timer_set(a2.id, "attack"))

    # ------------------------------------------------------------------
    # Counters
    # ------------------------------------------------------------------

    def test_counter_not_set_returns_default(self):
        agent = make_agent()
        self.assertIsNone(get_counter_elapsed_seconds(agent.id, "mission", default_value=None))

    def test_counter_starts_at_zero(self):
        agent = make_agent()
        start_counter(agent.id, "mission")
        self.assertEqual(get_counter_elapsed_seconds(agent.id, "mission"), 0)

    def test_counter_tracks_elapsed_seconds(self):
        agent = make_agent()
        start_counter(agent.id, "mission")
        advance_sim(30)
        self.assertEqual(get_counter_elapsed_seconds(agent.id, "mission"), 30)

    def test_clear_counter_removes_it(self):
        agent = make_agent()
        start_counter(agent.id, "mission")
        clear_counter(agent.id, "mission")
        self.assertIsNone(get_counter_elapsed_seconds(agent.id, "mission", default_value=None))

    # ------------------------------------------------------------------
    # Advancement via the REAL sim-time source (physics_tick), not by poking
    # _time_tick_counter directly. This is the path docking refit / timers ride
    # in a running mission, so it must actually move counters and timers.
    # ------------------------------------------------------------------

    def test_counter_advances_via_physics_tick(self):
        agent = make_agent()
        start_counter(agent.id, "refuel")
        sbs.resume_sim()                       # physics_tick is a no-op while paused
        for _ in range(60):                    # 60 * (1/30)s = 2 sim seconds
            sbs.physics_tick(1 / 30)
        self.assertAlmostEqual(get_counter_elapsed_seconds(agent.id, "refuel"), 2, delta=0.1)

    def test_timer_finishes_via_physics_tick(self):
        agent = make_agent()
        set_timer(agent.id, "warmup", seconds=2)
        sbs.resume_sim()
        for _ in range(30):                    # 1 sim second - not yet
            sbs.physics_tick(1 / 30)
        self.assertFalse(is_timer_finished(agent.id, "warmup"))
        for _ in range(45):                    # +1.5s -> 2.5s total - done
            sbs.physics_tick(1 / 30)
        self.assertTrue(is_timer_finished(agent.id, "warmup"))

    def test_physics_tick_paused_does_not_advance_counter(self):
        agent = make_agent()
        start_counter(agent.id, "idle")
        # sim starts paused; ticks must not advance the counter
        for _ in range(30):
            sbs.physics_tick(1 / 30)
        self.assertEqual(get_counter_elapsed_seconds(agent.id, "idle"), 0)


# ----------------------------------------------------------------------------
# timer_add_time
#
# A timer stores an ABSOLUTE sim tick, so every case below advances the sim clock
# BEFORE setting the timer. At tick 0 a duration and an absolute tick are the same
# number, which is exactly how PR #60 shipped a version that expired every timer it
# touched and still looked plausible.
# ----------------------------------------------------------------------------

class TestTimerAddTime(unittest.TestCase):

    def setUp(self):
        SpaceObject.clear()
        sbs.create_new_sim()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent())
        self.emits = []
        self.observer = lambda name, data: self.emits.append((name, data))
        signal_observe(self.observer)

    def tearDown(self):
        signal_unobserve(self.observer)

    def stored(self, agent, name):
        """The raw tick value a timer holds."""
        return get_inventory_value(agent.id, f"__timer__{name}")

    # ------------------------------------------------------------------
    # Extending
    # ------------------------------------------------------------------

    def test_add_extends_a_running_timer(self):
        agent = make_agent()
        advance_sim(100)
        set_timer(agent.id, "repair", seconds=10)
        advance_sim(3)
        timer_add_time(agent.id, "repair", seconds=5)
        self.assertEqual(get_time_remaining(agent.id, "repair"), 12)
        self.assertFalse(is_timer_finished(agent.id, "repair"))

    def test_added_time_actually_delays_expiry(self):
        agent = make_agent()
        advance_sim(100)
        set_timer(agent.id, "repair", seconds=5)
        timer_add_time(agent.id, "repair", seconds=5)
        advance_sim(6)
        self.assertFalse(is_timer_finished(agent.id, "repair"))
        advance_sim(5)
        self.assertTrue(is_timer_finished(agent.id, "repair"))

    def test_stored_target_is_an_absolute_tick(self):
        agent = make_agent()
        advance_sim(100)
        now = sbs.sim.time_tick_counter
        set_timer(agent.id, "repair", seconds=10)
        timer_add_time(agent.id, "repair", seconds=5)
        self.assertEqual(self.stored(agent, "repair"), now + 15 * TICK_PER_SECONDS)

    def test_add_minutes(self):
        agent = make_agent()
        advance_sim(100)
        set_timer(agent.id, "warp", seconds=30)
        timer_add_time(agent.id, "warp", minutes=1)
        self.assertEqual(get_time_remaining(agent.id, "warp"), 90)

    def test_add_seconds_and_minutes_combined(self):
        agent = make_agent()
        advance_sim(100)
        set_timer(agent.id, "mission", seconds=10)
        timer_add_time(agent.id, "mission", minutes=1, seconds=5)
        self.assertEqual(get_time_remaining(agent.id, "mission"), 75)

    def test_repeated_adds_do_not_drift(self):
        # Half a second in, so a seconds-rounded round trip would shed it each call.
        agent = make_agent()
        advance_sim(100)
        set_timer(agent.id, "cooldown", seconds=10)
        sbs.sim._time_tick_counter += TICK_PER_SECONDS // 2
        target = self.stored(agent, "cooldown")
        for _ in range(5):
            timer_add_time(agent.id, "cooldown", seconds=0)
        self.assertEqual(self.stored(agent, "cooldown"), target)

    # ------------------------------------------------------------------
    # Shortening
    # ------------------------------------------------------------------

    def test_negative_seconds_shorten(self):
        agent = make_agent()
        advance_sim(100)
        set_timer(agent.id, "cooldown", seconds=60)
        timer_add_time(agent.id, "cooldown", seconds=-50)
        self.assertEqual(get_time_remaining(agent.id, "cooldown"), 10)
        self.assertFalse(is_timer_finished(agent.id, "cooldown"))

    def test_large_negative_expires_the_timer(self):
        agent = make_agent()
        advance_sim(100)
        set_timer(agent.id, "cooldown", seconds=10)
        timer_add_time(agent.id, "cooldown", seconds=-600)
        self.assertTrue(is_timer_finished(agent.id, "cooldown"))
        # Finished, not erased - the stored value must never fall back to "unset".
        self.assertTrue(is_timer_set(agent.id, "cooldown"))
        self.assertTrue(is_timer_set_and_finished(agent.id, "cooldown"))

    # ------------------------------------------------------------------
    # No-ops
    # ------------------------------------------------------------------

    def test_no_op_when_timer_never_set(self):
        agent = make_agent()
        advance_sim(100)
        self.assertFalse(timer_add_time(agent.id, "never_set", seconds=30))
        self.assertFalse(is_timer_set(agent.id, "never_set"))

    def test_no_op_when_timer_already_finished(self):
        agent = make_agent()
        advance_sim(100)
        set_timer(agent.id, "repair", seconds=5)
        advance_sim(10)
        self.assertFalse(timer_add_time(agent.id, "repair", seconds=60))
        self.assertTrue(is_timer_finished(agent.id, "repair"))

    def test_returns_true_when_applied(self):
        agent = make_agent()
        advance_sim(100)
        set_timer(agent.id, "repair", seconds=5)
        self.assertTrue(timer_add_time(agent.id, "repair", seconds=5))

    # ------------------------------------------------------------------
    # Isolation
    # ------------------------------------------------------------------

    def test_other_timers_on_the_agent_are_unaffected(self):
        agent = make_agent()
        advance_sim(100)
        set_timer(agent.id, "fast", seconds=5)
        set_timer(agent.id, "slow", seconds=20)
        slow = self.stored(agent, "slow")
        timer_add_time(agent.id, "fast", seconds=10)
        self.assertEqual(self.stored(agent, "slow"), slow)

    def test_other_agents_are_unaffected(self):
        a1 = make_agent()
        a2 = make_agent()
        advance_sim(100)
        set_timer(a1.id, "repair", seconds=5)
        set_timer(a2.id, "repair", seconds=5)
        other = self.stored(a2, "repair")
        timer_add_time(a1.id, "repair", seconds=10)
        self.assertEqual(self.stored(a2, "repair"), other)

    # ------------------------------------------------------------------
    # timer_updated signal
    # ------------------------------------------------------------------

    def test_emits_timer_updated(self):
        agent = make_agent()
        advance_sim(100)
        set_timer(agent.id, "repair", seconds=10)
        timer_add_time(agent.id, "repair", seconds=5)
        updates = [d for n, d in self.emits if n == "timer_updated"]
        self.assertEqual(len(updates), 1)
        self.assertEqual(updates[0]["TIMER_AGENT_ID"], agent.id)
        self.assertEqual(updates[0]["TIMER_NAME"], "repair")

    def test_no_signal_when_nothing_changed(self):
        agent = make_agent()
        advance_sim(100)
        timer_add_time(agent.id, "never_set", seconds=5)
        set_timer(agent.id, "repair", seconds=5)
        advance_sim(10)
        timer_add_time(agent.id, "repair", seconds=5)
        self.assertEqual([d for n, d in self.emits if n == "timer_updated"], [])

    # ------------------------------------------------------------------
    # Via the real sim-time source
    # ------------------------------------------------------------------

    def test_add_survives_physics_tick(self):
        agent = make_agent()
        set_timer(agent.id, "warmup", seconds=2)
        sbs.resume_sim()
        for _ in range(30):                    # 1s in
            sbs.physics_tick(1 / 30)
        timer_add_time(agent.id, "warmup", seconds=2)
        for _ in range(45):                    # 2.5s total - the original would be done
            sbs.physics_tick(1 / 30)
        self.assertFalse(is_timer_finished(agent.id, "warmup"))
        for _ in range(60):                    # 4.5s total
            sbs.physics_tick(1 / 30)
        self.assertTrue(is_timer_finished(agent.id, "warmup"))



class TestTimerSignals(unittest.TestCase):
    """set_timer(signal=) and start_counter(signal=, interval=)."""

    def setUp(self):
        SpaceObject.clear()
        sbs.create_new_sim()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent())
        timer_signals_clear()
        TickDispatcher.clear()
        self.emits = []
        self.observer = lambda name, data: self.emits.append((name, data))
        signal_observe(self.observer)

    def tearDown(self):
        signal_unobserve(self.observer)
        timer_signals_clear()
        TickDispatcher.clear()

    def fired(self, name):
        return [d for n, d in self.emits if n == name]

    # ------------------------------------------------------------------
    # Timer completion
    # ------------------------------------------------------------------

    def test_no_signal_without_the_argument(self):
        agent = make_agent()
        set_timer(agent.id, "repair", seconds=5)
        self.assertEqual(timer_signals_count(), 0)
        advance_sim(10)
        _signals_tick()
        self.assertEqual(self.fired("repair_done"), [])

    def test_fires_once_at_expiry(self):
        agent = make_agent()
        set_timer(agent.id, "repair", seconds=5, signal="repair_done")
        advance_sim(10)
        _signals_tick()
        done = self.fired("repair_done")
        self.assertEqual(len(done), 1)
        self.assertEqual(done[0]["TIMER_AGENT_ID"], agent.id)
        self.assertEqual(done[0]["TIMER_NAME"], "repair")
        self.assertEqual(done[0]["TIMER_COUNT"], 1)
        # and never again
        advance_sim(60)
        _signals_tick()
        self.assertEqual(len(self.fired("repair_done")), 1)

    def test_does_not_fire_early(self):
        agent = make_agent()
        set_timer(agent.id, "repair", seconds=5, signal="repair_done")
        advance_sim(4)
        _signals_tick()
        self.assertEqual(self.fired("repair_done"), [])
        self.assertEqual(timer_signals_count(), 1)

    def test_polling_still_works_alongside(self):
        """The signal is additive - it must not disturb the inventory value."""
        agent = make_agent()
        set_timer(agent.id, "repair", seconds=5, signal="repair_done")
        advance_sim(10)
        _signals_tick()
        self.assertTrue(is_timer_set(agent.id, "repair"))
        self.assertTrue(is_timer_set_and_finished(agent.id, "repair"))

    def test_clear_timer_suppresses(self):
        agent = make_agent()
        set_timer(agent.id, "repair", seconds=5, signal="repair_done")
        clear_timer(agent.id, "repair")
        self.assertEqual(timer_signals_count(), 0)
        advance_sim(10)
        _signals_tick()
        self.assertEqual(self.fired("repair_done"), [])

    def test_reset_without_signal_disarms(self):
        agent = make_agent()
        set_timer(agent.id, "repair", seconds=5, signal="repair_done")
        set_timer(agent.id, "repair", seconds=5)
        self.assertEqual(timer_signals_count(), 0)
        advance_sim(10)
        _signals_tick()
        self.assertEqual(self.fired("repair_done"), [])

    def test_deleted_agent_suppresses(self):
        agent = make_agent()
        set_timer(agent.id, "repair", seconds=5, signal="repair_done")
        agent.remove()
        advance_sim(10)
        _signals_tick()
        self.assertEqual(self.fired("repair_done"), [])
        self.assertEqual(timer_signals_count(), 0)

    def test_extension_defers_the_signal(self):
        agent = make_agent()
        set_timer(agent.id, "repair", seconds=5, signal="repair_done")
        timer_add_time(agent.id, "repair", seconds=10)
        advance_sim(8)
        _signals_tick()
        self.assertEqual(self.fired("repair_done"), [])
        advance_sim(10)
        _signals_tick()
        self.assertEqual(len(self.fired("repair_done")), 1)

    def test_shortening_fires_early(self):
        agent = make_agent()
        set_timer(agent.id, "repair", minutes=5, signal="repair_done")
        advance_sim(5)
        timer_add_time(agent.id, "repair", minutes=-5)
        _signals_tick()
        self.assertEqual(len(self.fired("repair_done")), 1)

    def test_two_timers_on_one_agent_are_independent(self):
        agent = make_agent()
        set_timer(agent.id, "repair", seconds=5, signal="repair_done")
        set_timer(agent.id, "cooldown", seconds=20, signal="cooldown_done")
        advance_sim(10)
        _signals_tick()
        self.assertEqual(len(self.fired("repair_done")), 1)
        self.assertEqual(self.fired("cooldown_done"), [])
        advance_sim(20)
        _signals_tick()
        self.assertEqual(len(self.fired("cooldown_done")), 1)

    # ------------------------------------------------------------------
    # Counter heartbeat
    # ------------------------------------------------------------------

    def test_counter_beats_on_the_interval(self):
        agent = make_agent()
        set_interval(agent.id, "patrol", "beat", seconds=10)
        advance_sim(9)
        _signals_tick()
        self.assertEqual(self.fired("beat"), [])
        advance_sim(2)
        _signals_tick()
        self.assertEqual(len(self.fired("beat")), 1)
        advance_sim(10)
        _signals_tick()
        beats = self.fired("beat")
        self.assertEqual(len(beats), 2)
        self.assertEqual([b["TIMER_COUNT"] for b in beats], [1, 2])
        self.assertEqual(beats[0]["TIMER_NAME"], "patrol")

    def test_counter_beat_does_not_drift(self):
        """Beats are scheduled from the counter's start, not from when the tick
        happened to notice - a late tick must not push every later beat out."""
        agent = make_agent()
        set_interval(agent.id, "patrol", "beat", seconds=10)
        advance_sim(19)          # noticed 9s late
        _signals_tick()
        self.assertEqual(len(self.fired("beat")), 1)
        advance_sim(2)           # 21s in: the 20s beat is due
        _signals_tick()
        self.assertEqual(len(self.fired("beat")), 2)

    def test_counter_missed_beats_are_skipped_not_caught_up(self):
        agent = make_agent()
        set_interval(agent.id, "patrol", "beat", seconds=10)
        advance_sim(100)         # ten periods in one jump (e.g. a long pause)
        _signals_tick()
        self.assertEqual(len(self.fired("beat")), 1)

    def test_clear_counter_stops_the_beat(self):
        agent = make_agent()
        set_interval(agent.id, "patrol", "beat", seconds=10)
        advance_sim(11)
        _signals_tick()
        clear_counter(agent.id, "patrol")
        self.assertEqual(timer_signals_count(), 0)
        advance_sim(30)
        _signals_tick()
        self.assertEqual(len(self.fired("beat")), 1)

    def test_counter_reading_still_works(self):
        agent = make_agent()
        set_interval(agent.id, "patrol", "beat", seconds=10)
        advance_sim(15)
        self.assertEqual(int(get_counter_elapsed_seconds(agent.id, "patrol")), 15)

    def test_zero_period_is_refused(self):
        agent = make_agent()
        self.assertFalse(set_interval(agent.id, "patrol", "beat"))
        self.assertEqual(timer_signals_count(), 0)

    def test_clear_interval_stops_the_beat(self):
        agent = make_agent()
        set_interval(agent.id, "patrol", "beat", seconds=10)
        clear_interval(agent.id, "patrol")
        self.assertEqual(timer_signals_count(), 0)
        advance_sim(30)
        _signals_tick()
        self.assertEqual(self.fired("beat"), [])

    def test_restarting_the_counter_restarts_the_beat(self):
        agent = make_agent()
        set_interval(agent.id, "patrol", "beat", seconds=10)
        advance_sim(9)
        start_counter(agent.id, "patrol")     # re-anchor 1s before the beat
        advance_sim(2)           # 11s since the FIRST start, 2s since the restart
        _signals_tick()
        self.assertEqual(self.fired("beat"), [])
        advance_sim(9)
        _signals_tick()
        self.assertEqual(len(self.fired("beat")), 1)

    # ------------------------------------------------------------------
    # The tick task is lazy
    # ------------------------------------------------------------------

    def test_no_tick_task_when_unused(self):
        agent = make_agent()
        set_timer(agent.id, "repair", seconds=5)
        start_counter(agent.id, "docked")
        TickDispatcher.dispatch_tick()
        self.assertEqual(len(TickDispatcher._dispatch_tick), 0)

    def test_tick_task_is_created_and_then_stops(self):
        agent = make_agent()
        set_timer(agent.id, "repair", seconds=5, signal="repair_done")
        TickDispatcher.dispatch_tick()
        self.assertEqual(len(TickDispatcher._dispatch_tick), 1)
        advance_sim(10)
        TickDispatcher.dispatch_tick()          # fires, disarms, stops itself
        self.assertEqual(len(self.fired("repair_done")), 1)
        TickDispatcher.dispatch_tick()
        self.assertEqual(len(TickDispatcher._dispatch_tick), 0)

    def test_clear_drops_everything(self):
        agent = make_agent()
        set_timer(agent.id, "repair", seconds=5, signal="repair_done")
        set_interval(agent.id, "patrol", "beat", seconds=10)
        self.assertEqual(timer_signals_count(), 2)
        timer_signals_clear()
        self.assertEqual(timer_signals_count(), 0)
        advance_sim(60)
        _signals_tick()
        self.assertEqual(self.emits, [])

    # ------------------------------------------------------------------
    # Reaching the ROUTES, not just the observers
    #
    # Every test above asserts through signal_observe, which runs before
    # signal_emit even looks at the MAST context - so all of them passed while
    # no //signal route ran at all. These two watch the handoff itself.
    # ------------------------------------------------------------------

    def test_a_timer_emit_is_not_attributed_to_a_finished_task(self):
        """The scheduler leaves its last task in FrameContext.task and never restores
        it, so by the time the timer tick runs that task is usually DONE. Passing it
        as the sender makes MastAsyncTask.emit_signal drop the emit at its
        `sender_task.done()` guard: the signal fires and every route silently does
        nothing. A timer speaks for no task."""
        agent = make_agent()
        set_timer(agent.id, "repair", seconds=5, signal="repair_done")
        seen = []

        class _FinishedTask:
            def done(self):
                return True

        class _RecordingMast:
            def signal_emit(self, name, sender_task, data):
                seen.append((name, sender_task, data))

        held_mast, held_task = FrameContext.mast, FrameContext._task
        FrameContext.mast, FrameContext._task = _RecordingMast(), _FinishedTask()
        try:
            advance_sim(10)
            _signals_tick()
        finally:
            FrameContext.mast, FrameContext._task = held_mast, held_task

        self.assertEqual(len(seen), 1, "the emit never reached the story")
        name, sender, data = seen[0]
        self.assertEqual(name, "repair_done")
        self.assertIsNone(
            sender, "a finished sender task makes emit_signal drop every route")
        self.assertEqual(data["TIMER_NAME"], "repair")

    def test_the_timer_tick_leaves_the_frame_task_as_it_found_it(self):
        """Overriding the sender must not leak: the tick runs inside someone else's
        frame, and the next thing to read FrameContext.task is not ours."""
        agent = make_agent()
        set_interval(agent.id, "patrol", "beat", seconds=5)
        marker = object()
        held = FrameContext._task
        FrameContext._task = marker
        try:
            advance_sim(10)
            _signals_tick()
            self.assertIs(FrameContext._task, marker)
        finally:
            FrameContext._task = held


class TestServerTimers(unittest.TestCase):
    """id 0 is the SERVER, and a timer put there has to stay there.

    Every other test in this file uses `make_agent()`, which hands out a fresh
    `get_story_id()` - so nothing here ever touched id 0, and that is the whole reason
    LM #719 got out. `to_object(0)` returns None on purpose (for a space object, 0 means
    "no object"), `set_inventory_value` resolved through it for a while, and every timer
    and counter writes through `set_inventory_value`. So `start_counter(0, name)` wrote
    nothing and `get_counter_elapsed_seconds(0, name)` answered None forever.

    `set_timer(0, ...)` failed worse than that. An unset timer counts as FINISHED, so
    `is_timer_finished(0, name)` answered True on the first pass - which is a mission
    whose timed loop ends immediately, with no error anywhere. SecretMeeting's meeting
    and the `sbs create` sandbox template's clock are both exactly that shape.

    `id 0 = server` is a documented idiom (writing-a-mission SKILL.md says so), so these
    are the contract, not a corner case.

        python -m unittest tests.test_timers.TestServerTimers
    """

    def setUp(self):
        SpaceObject.clear()
        sbs.create_new_sim()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent())
        timer_signals_clear()
        TickDispatcher.clear()
        # What Gui.present builds on the first server frame. Nothing else in the library
        # registers an Agent at id 0.
        self.server = GuiClient(0)
        self.emits = []
        self.observer = lambda name, data: self.emits.append((name, data))
        signal_observe(self.observer)

    def tearDown(self):
        signal_unobserve(self.observer)
        timer_signals_clear()
        TickDispatcher.clear()
        # A leaked Agent.all[0] outlives this file and poisons the next one.
        SpaceObject.clear()

    def fired(self, name):
        return [d for n, d in self.emits if n == name]

    # ------------------------------------------------------------------
    # Counters - the reported symptom
    # ------------------------------------------------------------------

    def test_counter_on_the_server_reports_elapsed_seconds(self):
        """LM #719, verbatim."""
        start_counter(0, "Mission_Elapsed_Time")
        advance_sim(10)
        self.assertEqual(
            10.0, get_counter_elapsed_seconds(0, "Mission_Elapsed_Time"),
            "the counter answered None - the write never reached the server agent")

    def test_counter_on_the_server_starts_at_zero(self):
        """0.0, not None. A counter that was never written reads as the default, and
        the default is what a caller passes - so only an explicit 0.0 tells the two
        apart."""
        start_counter(0, "clock")
        self.assertEqual(0.0, get_counter_elapsed_seconds(0, "clock"))

    def test_clear_counter_on_the_server(self):
        start_counter(0, "clock")
        clear_counter(0, "clock")
        self.assertIsNone(get_counter_elapsed_seconds(0, "clock"))

    # ------------------------------------------------------------------
    # Timers - the same write, with a worse failure
    # ------------------------------------------------------------------

    def test_timer_on_the_server_is_not_finished_immediately(self):
        """The one that ends missions. An unset timer counts as finished, so a dropped
        write is indistinguishable from a timer that already expired."""
        set_timer(0, "meeting", minutes=1)
        self.assertTrue(is_timer_set(0, "meeting"))
        self.assertFalse(
            is_timer_finished(0, "meeting"),
            "a one-minute timer reported finished on the tick it was set")

    def test_timer_on_the_server_finishes_after_its_duration(self):
        set_timer(0, "meeting", minutes=1)
        advance_sim(61)
        self.assertTrue(is_timer_finished(0, "meeting"))
        self.assertTrue(is_timer_set_and_finished(0, "meeting"))

    def test_clear_timer_on_the_server(self):
        set_timer(0, "meeting", minutes=1)
        clear_timer(0, "meeting")
        self.assertFalse(is_timer_set(0, "meeting"))

    def test_get_time_remaining_on_the_server(self):
        """Asserted as PARITY with an ordinary agent rather than against a literal.
        `get_time_remaining` answers -1 for an expired timer while its docstring
        promises 0 - a separate, pre-existing bug. Whichever way that is settled, the
        server must answer the same as everyone else, which is what this file is for."""
        other = make_agent()
        set_timer(0, "meeting", seconds=30)
        set_timer(other.id, "meeting", seconds=30)
        self.assertEqual(30, get_time_remaining(0, "meeting"))
        advance_sim(31)
        self.assertEqual(get_time_remaining(other.id, "meeting"),
                         get_time_remaining(0, "meeting"))

    # ------------------------------------------------------------------
    # The armed forms, which fail their own way
    # ------------------------------------------------------------------

    def test_timer_signal_on_the_server_fires(self):
        """SecretMeeting's shape. This one does not merely read wrong: `_signals_tick`
        re-validates the armed entry against the inventory it was anchored to, so a
        dropped write makes it DISARM without ever emitting - the signal simply never
        arrives, and nothing says why."""
        set_timer(0, "meeting_count", seconds=5, signal="meeting_over")
        advance_sim(10)
        _signals_tick()
        done = self.fired("meeting_over")
        self.assertEqual(len(done), 1, "the armed timer disarmed instead of firing")
        self.assertEqual(done[0]["TIMER_AGENT_ID"], 0)
        self.assertEqual(done[0]["TIMER_NAME"], "meeting_count")

    def test_interval_on_the_server_beats(self):
        set_interval(0, "gm_beat", "beat", seconds=10)
        advance_sim(11)
        _signals_tick()
        self.assertEqual(len(self.fired("beat")), 1)
        advance_sim(10)
        _signals_tick()
        beats = self.fired("beat")
        self.assertEqual([b["TIMER_COUNT"] for b in beats], [1, 2])
        self.assertEqual(beats[0]["TIMER_AGENT_ID"], 0)


if __name__ == '__main__':
    unittest.main()
