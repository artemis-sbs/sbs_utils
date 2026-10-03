"""`Action:` fires when a beat STARTS - on every way a beat starts.

Found by the first dialogue lesson. The shortest way to place a call is the one the docs
lead with:

    #### [Take the Case](brief)
    ---
    Starts when: at once
    Action:
      - quill hails brief_scene
    ---

and it did nothing: lint clean, the quest ACTIVE, no call, no message. `quest_run_action`
was reached only from `quest_mark_active`, and neither of these paths goes through it:

  * a quest GRANTED already running - `Starts when: at once`, and the default for a Beat,
    an Arc and an Objective - has its state written by `quest_add`;
  * a quest that starts on a TRIGGER - `Starts when: signal alarm` - is armed and then
    swapped in by `quest_mark_complete`.

Only `Starts when: revealed` plus a reveal worked. An earlier fix said it had covered all
of these and tested `quest_mark_active` by calling it directly.

Everything here goes in the front door: AMD text, `quest_grant_amd`, then the driver's
own tick and signal handlers.

    python -m unittest tests.test_quest_action_on_every_start
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
from sbs_utils.procedural.quest import QuestState, quest_get_data, quest_get_state

VERB = "test pings"

AT_ONCE = """# [Mission](mission)

## [Quests](quests)

### [Take the Case](brief)
---
Scope: shared
Starts when: at once
Done when: signal case_closed
Action:
  - tower test pings brief
---
"""

A_BEAT = """# [Mission](mission)

## [Quests](quests)

### [The Station Calls](calls)
---
Beat
Action:
  - tower test pings calls
---
"""

ON_A_SIGNAL = """# [Mission](mission)

## [Quests](quests)

### [The Alarm](alarm_beat)
---
Beat
Starts when: signal alarm
Done when: 20 seconds
Action:
  - tower test pings alarm_beat
---
"""

OFFERED = """# [Mission](mission)

## [Quests](quests)

### [A job on the board](job)
---
Job
Scope: shared
State: idle
Done when: signal job_done
Action:
  - tower test pings job
---
"""


class _Base(unittest.TestCase):
    def setUp(self):
        reset_mock(sbs)
        self.pings = []
        self._had = amd_action._VERBS.get(VERB)

        def ping(actor, operand, line):
            self.pings.append(operand)

        amd_action._VERBS[VERB] = {"fn": ping, "operand": "required", "operand_ref": None}
        self.addCleanup(self._restore)

    def _restore(self):
        if self._had is None:
            amd_action._VERBS.pop(VERB, None)
        else:
            amd_action._VERBS[VERB] = self._had

    def grant(self, text):
        # The SECTION, as a mission's map body hands it over - not the document, whose
        # one child is the section itself.
        doc = amd_document(text, data_parser=amd_quest_data)
        QD.quest_grant_amd(Agent.SHARED_ID, amd_section(doc, "quests"))


class GrantedAlreadyRunningTests(_Base):
    def test_the_fixture_is_a_running_quest(self):
        self.grant(AT_ONCE)
        self.assertEqual(quest_get_state(Agent.SHARED_ID, "brief"), QuestState.ACTIVE)

    def test_nothing_fires_at_the_grant(self):
        """A map grants its quests before it spawns anything: nobody is there to hail."""
        self.grant(AT_ONCE)
        self.assertEqual(self.pings, [])
        self.assertEqual(QD.quest_actions_owed(), 1)

    def test_the_first_tick_runs_it(self):
        self.grant(AT_ONCE)
        QD.quest_tick_fail_after()            # what the mission's watcher calls
        self.assertEqual(self.pings, ["brief"])

    def test_and_only_once(self):
        self.grant(AT_ONCE)
        QD.quest_tick_fail_after()
        QD.quest_tick_fail_after()
        self.assertEqual(self.pings, ["brief"])
        self.assertEqual(QD.quest_actions_owed(), 0)

    def test_a_beat_with_no_starts_when_is_the_same(self):
        self.grant(A_BEAT)
        QD.quest_tick_actions()
        self.assertEqual(self.pings, ["calls"])

    def test_an_offered_quest_owes_nothing_until_it_is_taken(self):
        self.grant(OFFERED)
        QD.quest_tick_actions()
        self.assertEqual(self.pings, [])
        QD.quest_mark_active(Agent.SHARED_ID, "job")
        self.assertEqual(self.pings, ["job"])

    def test_a_regrant_does_not_run_it_again(self):
        self.grant(AT_ONCE)
        QD.quest_tick_actions()
        self.grant(AT_ONCE)
        QD.quest_tick_actions()
        self.assertEqual(self.pings, ["brief"])

    def test_a_mission_reset_owes_nothing(self):
        self.grant(AT_ONCE)
        reset_mock(sbs)
        self.assertEqual(QD.quest_actions_owed(), 0)


class StartedByATriggerTests(_Base):
    # A BEAT, deliberately. A record with no kind word is granted IDLE - on the board -
    # and its start trigger is not watched until somebody accepts it. That is its own
    # question; this class is about a beat that is running and waiting to start.
    def test_nothing_fires_while_it_waits(self):
        self.grant(ON_A_SIGNAL)
        QD.quest_tick_fail_after()
        self.assertEqual(self.pings, [])

    def test_the_trigger_starts_it_and_the_action_runs(self):
        self.grant(ON_A_SIGNAL)
        QD.quest_on_signal("alarm")
        self.assertEqual(self.pings, ["alarm_beat"])
        self.assertEqual(quest_get_state(Agent.SHARED_ID, "alarm_beat"), QuestState.ACTIVE)

    def test_a_timed_goal_waits_for_the_start(self):
        """`Done when: 20 seconds` was left live while the quest waited for its signal,
        so its clock ran from the grant and it could finish before it had begun."""
        self.grant(ON_A_SIGNAL)
        data = quest_get_data(Agent.SHARED_ID, "alarm_beat")
        self.assertNotIn("complete_after", data)
        self.assertIn("complete_after", data.get("armed_trigger") or {})

    def test_the_timed_goal_is_live_once_it_has_started(self):
        self.grant(ON_A_SIGNAL)
        QD.quest_on_signal("alarm")
        data = quest_get_data(Agent.SHARED_ID, "alarm_beat")
        self.assertIn("complete_after", data)
        self.assertNotIn("armed_trigger", data)


if __name__ == "__main__":
    unittest.main()
