from cosmos_dev.mock import sbs as sbs
from sbs_utils.spaceobject import SpaceObject
from sbs_utils.agent import Agent, get_story_id
from sbs_utils.helpers import FrameContext, Context, FakeEvent
from sbs_utils.fs import test_set_exe_dir
from sbs_utils.procedural.timers import (
    set_timer, is_timer_set, is_timer_finished, is_timer_set_and_finished,
    clear_timer, get_time_remaining, format_time_remaining,
    start_counter, get_counter_elapsed_seconds, clear_counter,
    TICK_PER_SECONDS,
)
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


if __name__ == '__main__':
    unittest.main()
