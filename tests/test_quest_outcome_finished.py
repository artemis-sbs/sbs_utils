"""A finished quest stays finished when a late answer names it.

Found by the lesson "Hails":

  * Two ships each hear the same offer. The second says yes after the first has done the
    job and been paid; `; accepts tag_hulk` started it again, and it paid twice.
  * A step with a deadline fails; its call is still waiting in the list. Answering it
    late ran `; completes report_in`, which un-failed the quest and paid the reward over
    the penalty.

Front door: AMD quests through `quest_grant_amd`, and the answer's outcomes through
`dialogue_apply`, the call an answered hail makes.

    python -m unittest tests.test_quest_outcome_finished
"""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import sbs_utils.mast_sbs.story_nodes  # noqa: F401
from cosmos_dev.mock import sbs as sbs
from tests.reset_helper import reset_mock

from sbs_utils.agent import Agent
from sbs_utils.procedural import quest_driver as QD
from sbs_utils.procedural.amd_dialogue import dialogue_apply
from sbs_utils.procedural.amd_doc import amd_document, amd_section
from sbs_utils.procedural.amd_quest import amd_quest_data
from sbs_utils.procedural.quest import QuestState, quest_get_state
from sbs_utils.procedural.signal import signal_observe, signal_unobserve

QUESTS = """# [Mission](mission)

## [Quests](quests)

### [Tag the Hulk](tag_hulk)
---
Scope: shared
Starts when: revealed
Done when: signal beacon_set
---

### [Report to DS 1](report_in)
---
Scope: shared
Starts when: at once
Done when: signal never_sent
---
"""


class LateAnswerTests(unittest.TestCase):
    def setUp(self):
        reset_mock(sbs)
        sbs.resume_sim()
        doc = amd_document(QUESTS, data_parser=amd_quest_data)
        QD.quest_grant_amd(Agent.SHARED_ID, amd_section(doc, "quests"))
        self.started, self.succeeded = [], []
        signal_observe(self._watch)
        self.addCleanup(signal_unobserve, self._watch)

    def _watch(self, name, data=None):
        if name == "quest_started":
            self.started.append((data or {}).get("QUEST_ID"))
        if name == "quest_succeeded":
            self.succeeded.append((data or {}).get("QUEST_ID"))

    def state(self, key):
        return quest_get_state(Agent.SHARED_ID, key)

    def answer(self, *outcome):
        self.assertTrue(dialogue_apply(None, None, [list(outcome)]) is not False)

    def test_a_yes_takes_the_job(self):
        self.answer("accepts", "tag_hulk")
        self.assertEqual(self.state("tag_hulk"), QuestState.ACTIVE)
        self.assertEqual(self.started.count("tag_hulk"), 1)

    def test_a_second_yes_after_it_is_done_does_not_start_it_again(self):
        self.answer("accepts", "tag_hulk")
        QD.quest_mark_complete(Agent.SHARED_ID, "tag_hulk")
        self.assertEqual(self.state("tag_hulk"), QuestState.COMPLETE)
        self.answer("accepts", "tag_hulk")
        self.assertEqual(self.state("tag_hulk"), QuestState.COMPLETE)
        self.assertEqual(self.started.count("tag_hulk"), 1)

    def test_a_late_report_does_not_un_fail_the_step(self):
        QD.quest_mark_failed(Agent.SHARED_ID, "report_in")
        self.assertEqual(self.state("report_in"), QuestState.FAILED)
        self.answer("completes", "report_in")
        self.assertEqual(self.state("report_in"), QuestState.FAILED)
        self.assertEqual(self.succeeded, [])

    def test_a_report_in_time_finishes_it_once(self):
        self.answer("completes", "report_in")
        self.answer("completes", "report_in")
        self.assertEqual(self.state("report_in"), QuestState.COMPLETE)
        self.assertEqual(self.succeeded.count("report_in"), 1)

    def test_fails_does_not_undo_a_finished_job(self):
        self.answer("completes", "report_in")
        self.answer("fails", "report_in")
        self.assertEqual(self.state("report_in"), QuestState.COMPLETE)


if __name__ == "__main__":
    unittest.main()
