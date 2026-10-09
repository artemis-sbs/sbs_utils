"""What a mission that SAVES needs from the quest driver to put a story back.

A mission that saves grants its story from the file again on every Continue and then
merges the saved state onto it. Three things the fresh grant gets wrong, and the driver
function that puts each right:

* a step written `Starts when: <trigger>` is granted ARMED - so a step that started last
  evening came back waiting for a signal that had already been sent
  (`quest_restore_started`);
* a `Fails when: 5 minutes` clock is an agent timer against the sim's own time, which
  starts again at zero - so it came back full (`quest_clocks` / `quest_clocks_restore`);
* a step granted already running owes its `Action:` to the first tick - so the grant on
  Continue ran the block of a step finished a week ago a second time
  (`quest_action_settle`). MEASURED here first: `TheActionOfAFinishedStep.test_GAP_16...`
  is the replay, on the unmodified grant-then-set-state sequence.

None of the three announces anything: no `Action:`, no signal, no reward.

    python -m unittest tests.test_quest_restore
"""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import sbs_utils.mast_sbs.story_nodes  # noqa: F401
from cosmos_dev.mock import sbs
from tests.reset_helper import reset_mock

from sbs_utils.agent import Agent
from sbs_utils.handlerhooks import reset_mission_state
from sbs_utils.mast.mast_globals import MastGlobals
from sbs_utils.procedural import quest_driver as QD
from sbs_utils.procedural.amd_doc import amd_document, amd_section
from sbs_utils.procedural.amd_mission import amd_mission_data
from sbs_utils.procedural.quest import (QuestState, quest_get_data, quest_get_state,
                                        quest_set_key)
from sbs_utils.procedural.signal import signal_observe, signal_unobserve
from sbs_utils.procedural.timers import get_time_remaining, is_timer_set

SHARED = Agent.SHARED_ID

STORY = """# [Mission](mission)

## [Quests](quests)

### [The Alarm](alarm)
---
Beat
Starts when: signal alarm_raised
Done when: signal alarm_cleared
Action:
  - yard becomes alert
---
Waits for the alarm, then for the all-clear.

### [The Countdown](countdown)
---
Beat
Starts when: at once
Done when: signal reached_port
Fails when: 60 seconds
Penalty: 50 credits
---
Sixty seconds to make port.

### [The Greeting](greeting)
---
Beat
Starts when: at once
Done when: signal greeted
Action:
  - yard becomes open
---
Runs the moment the story starts.

### [The Later Step](later)
---
Beat
Starts when: revealed
Done when: signal later_done
---
"""


class _Base(unittest.TestCase):
    def setUp(self):
        self.signals = []
        self.launch()
        self.addCleanup(reset_mission_state)
        self.addCleanup(signal_unobserve, self._watch)
        self.ran = []
        real = QD.quest_run_action
        QD.quest_run_action = lambda agent, qid: self.ran.append(qid) or 0
        self.addCleanup(setattr, QD, "quest_run_action", real)

    def _watch(self, name, data=None):
        self.signals.append((name, dict(data or {})))

    def launch(self):
        """A new process as far as the driver can tell, and the story granted from its
        file - which is what a Continue does before it restores anything."""
        signal_unobserve(self._watch)
        reset_mock(sbs)
        sbs.resume_sim()
        del self.signals[:]
        signal_observe(self._watch)
        doc = amd_document(STORY, data_parser=amd_mission_data)
        QD.quest_grant_amd(SHARED, amd_section(doc, "quests"))

    def seconds(self, n):
        sbs.sim._time_tick_counter += int(n * 30)

    def tick(self):
        QD.quest_tick_fail_after()
        QD.quest_tick_complete_after()

    def names(self):
        return [name for name, _data in self.signals]


class AStepThatHadStarted(_Base):
    def test_a_fresh_grant_is_armed_with_the_start_trigger(self):
        data = quest_get_data(SHARED, "alarm")
        self.assertIn("armed_trigger", data)
        self.assertEqual(data["on_signal"], {"name": "alarm_raised"})

    def test_restore_started_puts_the_real_trigger_in_and_says_nothing(self):
        self.assertTrue(QD.quest_restore_started(SHARED, "alarm"))
        data = quest_get_data(SHARED, "alarm")
        self.assertNotIn("armed_trigger", data)
        self.assertEqual(data["on_signal"], {"name": "alarm_cleared"})
        self.assertEqual(self.ran, [], "its Action: ran the evening it started")
        self.assertNotIn("quest_started", self.names())
        self.assertNotIn("quest_succeeded", self.names())

    def test_the_all_clear_then_finishes_it(self):
        QD.quest_restore_started(SHARED, "alarm")
        QD.quest_on_signal("alarm_cleared")
        self.assertEqual(quest_get_state(SHARED, "alarm"), QuestState.COMPLETE)

    def test_without_it_the_all_clear_only_starts_the_step_again(self):
        """The fault: armed again, the step waits for `alarm_raised`, so the signal that
        should finish it is not even heard."""
        QD.quest_on_signal("alarm_cleared")
        self.assertEqual(quest_get_state(SHARED, "alarm"), QuestState.ACTIVE)
        self.assertIn("armed_trigger", quest_get_data(SHARED, "alarm"))

    def test_a_step_that_is_not_waiting_is_left_alone(self):
        self.assertFalse(QD.quest_restore_started(SHARED, "greeting"))
        self.assertFalse(QD.quest_restore_started(SHARED, "no_such_step"))
        QD.quest_restore_started(SHARED, "alarm")
        self.assertFalse(QD.quest_restore_started(SHARED, "alarm"), "once")


class AClockHalfRun(_Base):
    def test_the_time_left_is_what_is_written_down(self):
        self.assertEqual(QD.quest_clocks(SHARED, "countdown"), {}, "not running yet")
        self.tick()                                   # the driver starts the clock
        self.assertEqual(QD.quest_clocks(SHARED, "countdown"), {"fail": 60})
        self.seconds(25)
        self.assertEqual(QD.quest_clocks(SHARED, "countdown"), {"fail": 35})

    def test_it_comes_back_with_the_time_that_was_left(self):
        self.tick()
        self.seconds(25)
        left = QD.quest_clocks(SHARED, "countdown")
        self.launch()                                 # tomorrow
        self.assertEqual(QD.quest_clocks_restore(SHARED, "countdown", left), 1)
        self.tick()
        self.assertEqual(get_time_remaining(SHARED, "qfail:countdown"), 35,
                         "the first tick finds a clock running and does not start a full one")
        self.seconds(30)
        self.tick()
        self.assertEqual(quest_get_state(SHARED, "countdown"), QuestState.ACTIVE)
        self.seconds(6)
        self.tick()
        self.assertEqual(quest_get_state(SHARED, "countdown"), QuestState.FAILED)

    def test_without_it_the_clock_is_full_again(self):
        self.tick()
        self.seconds(25)
        self.launch()
        self.tick()
        self.assertEqual(get_time_remaining(SHARED, "qfail:countdown"), 60)

    def test_a_clock_that_is_not_running_or_has_run_out_is_not_written(self):
        self.tick()
        self.seconds(61)
        self.assertEqual(QD.quest_clocks(SHARED, "countdown"), {})
        self.assertEqual(QD.quest_clocks_restore(SHARED, "countdown", {}), 0)
        self.assertEqual(QD.quest_clocks_restore(SHARED, "countdown", None), 0)
        self.assertEqual(QD.quest_clocks_restore(SHARED, "countdown", {"fail": 0}), 0)
        self.assertEqual(QD.quest_clocks_restore(SHARED, "countdown", {"fail": "x"}), 0)
        self.assertFalse(is_timer_set(SHARED, "qdone:countdown"))


class TheActionOfAFinishedStep(_Base):
    def test_a_new_game_runs_the_action_of_a_step_granted_running(self):
        self.assertEqual(QD.quest_actions_owed(), 1, "the greeting; the alarm is armed")
        self.tick()
        self.assertEqual(self.ran, ["greeting"])

    def test_GAP_16_the_action_replays_on_a_continue(self):
        """MEASURED. What a Continue did: grant the story, then set the saved state. The
        greeting was finished last week, and its block runs again on the first tick."""
        quest_set_key(SHARED, "greeting", "state", QuestState.COMPLETE)
        self.tick()
        self.assertEqual(self.ran, ["greeting"], "the replay")

    def test_settled_it_does_not(self):
        quest_set_key(SHARED, "greeting", "state", QuestState.COMPLETE)
        self.assertTrue(QD.quest_action_settle(SHARED, "greeting"))
        self.assertEqual(QD.quest_actions_owed(), 0)
        self.tick()
        self.assertEqual(self.ran, [])

    def test_settling_one_step_leaves_the_others_owed(self):
        self.assertFalse(QD.quest_action_settle(SHARED, "countdown"), "it owed nothing")
        self.assertFalse(QD.quest_action_settle(SHARED, "no_such_step"))
        self.assertEqual(QD.quest_actions_owed(), 1)
        self.tick()
        self.assertEqual(self.ran, ["greeting"])


class MastCanCallThem(unittest.TestCase):
    def test_they_are_mast_globals(self):
        import sbs_utils.mast_sbs.mast_sbs_procedural  # noqa: F401
        for name in ("quest_restore_started", "quest_clocks", "quest_clocks_restore",
                     "quest_action_settle"):
            self.assertIn(name, MastGlobals.globals, name)


if __name__ == "__main__":
    unittest.main()
