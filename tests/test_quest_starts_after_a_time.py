"""`Starts when: 5 seconds` starts the quest five seconds in.

Found by the lesson "Hails". A beat that says

    ### [Quill Calls](quill_calls)
    ---
    Beat
    Starts when: 5 seconds
    Action:
      - tower test pings quill_calls
    ---

sat ACTIVE and never started: no call, lint clean, the run passed, and the format page
says "`Starts when: 3 seconds` works". The start trigger was armed under the reader's name
for a time (`after`); the watcher looks for `complete_after`.

Front door: AMD text, `quest_grant_amd`, the driver's own ticks, the sim's own clock.

    python -m unittest tests.test_quest_starts_after_a_time
"""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import sbs_utils.mast_sbs.story_nodes  # noqa: F401
from cosmos_dev.mock import sbs as sbs
from tests.reset_helper import reset_mock

from sbs_utils.agent import Agent
from sbs_utils.procedural import amd_action
from sbs_utils.procedural import quest_driver as QD
from sbs_utils.procedural.amd_doc import amd_document, amd_section
from sbs_utils.procedural.amd_quest import amd_quest_data
from sbs_utils.procedural.quest import QuestState, quest_get_state

VERB = "test pings"

TIMED_START = """# [Mission](mission)

## [Quests](quests)

### [Quill Calls](quill_calls)
---
Beat
Starts when: 5 seconds
Done when: {done}
Action:
  - tower test pings quill_calls
---
"""


class TimedStartTests(unittest.TestCase):
    def setUp(self):
        reset_mock(sbs)
        sbs.resume_sim()
        self.pings = []
        had = amd_action._VERBS.get(VERB)

        def ping(actor, operand, line):
            self.pings.append(operand)

        amd_action._VERBS[VERB] = {"fn": ping, "operand": "required", "operand_ref": None}

        def restore():
            if had is None:
                amd_action._VERBS.pop(VERB, None)
            else:
                amd_action._VERBS[VERB] = had

        self.addCleanup(restore)

    def grant(self, done="signal call_over"):
        doc = amd_document(TIMED_START.format(done=done), data_parser=amd_quest_data)
        QD.quest_grant_amd(Agent.SHARED_ID, amd_section(doc, "quests"))

    def seconds(self, n):
        """Let `n` seconds of game time pass, ticking the driver once a second."""
        for _ in range(n):
            sbs.sim._time_tick_counter += 30
            QD.quest_tick_complete_after()
            QD.quest_tick_fail_after()
            QD.quest_tick_actions()

    def state(self):
        return quest_get_state(Agent.SHARED_ID, "quill_calls")

    def test_nothing_happens_before_the_time(self):
        self.grant()
        self.seconds(3)
        self.assertEqual(self.pings, [])

    def test_the_beat_starts_at_the_time_and_its_action_runs_once(self):
        self.grant()
        self.seconds(8)
        self.assertEqual(self.pings, ["quill_calls"])
        self.seconds(8)
        self.assertEqual(self.pings, ["quill_calls"])
        self.assertEqual(self.state(), QuestState.ACTIVE)      # waiting on its signal

    def test_starting_is_not_finishing(self):
        self.grant()
        self.seconds(8)
        self.assertNotEqual(self.state(), QuestState.COMPLETE)

    def test_a_timed_finish_behind_a_timed_start_takes_its_own_time(self):
        self.grant(done="20 seconds")
        self.seconds(8)                       # started at 5
        self.assertEqual(self.pings, ["quill_calls"])
        self.assertEqual(self.state(), QuestState.ACTIVE)
        self.seconds(10)                      # 13 into its 20
        self.assertEqual(self.state(), QuestState.ACTIVE)
        self.seconds(14)
        self.assertEqual(self.state(), QuestState.COMPLETE)


if __name__ == "__main__":
    unittest.main()
