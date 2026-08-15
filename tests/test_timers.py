from cosmos_dev.mock import sbs as sbs
from sbs_utils.spaceobject import SpaceObject
from sbs_utils.agent import Agent, get_story_id
from sbs_utils.helpers import FrameContext, Context, FakeEvent
from sbs_utils.fs import test_set_exe_dir
from sbs_utils.procedural.timers import (
    set_timer, is_timer_set, is_timer_finished, is_timer_set_and_finished,
    clear_timer, get_time_remaining, format_time_remaining, timer_add_time,
    start_counter, get_counter_elapsed_seconds, clear_counter,
    TICK_PER_SECONDS,
)
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


if __name__ == '__main__':
    unittest.main()
