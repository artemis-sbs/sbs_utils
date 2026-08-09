"""Three quest bugs that were each silent in their own way.

RE-GRANT WIPED NESTED PROGRESS. quest_grant_amd guarded with
`quest_get_state(...) == IDLE`, and quest_get_state returns IDLE both for a quest
that does not exist AND for one that exists and is merely OFFERED. So a re-grant
ran quest_add over every unaccepted quest, and quest_add builds a FRESH node with
`"children": {}` - discarding any nested arc step underneath it, however far along.
A re-grant is not exotic: it happens on the Open Universe Continue path and on a
map restart.

`Action:` NEVER FIRED ON THE PATHS AUTHORS USE. quest_run_action was reachable only
from quest.quest_set_state; the driver writes state directly through quest_set_key.
So the block was dead on the Accept button, on `Then: reveal`, on a quest granted
ACTIVE (the DEFAULT for Beat/Arc/Objective), and on a `Starts when:` swap-in - which
is the path the one documented example in amd-format.md takes.

quest_on_signal STILL SCANNED `[SHARED] + players`. Every sibling handler had moved
to _quest_holders(), whose docstring says why: the old pattern silently skips a
quest granted to a station or a side, so a `Held by:` job's `Done when: signal`
never advanced and nothing logged, because nothing looked.
"""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

from sbs_utils.agent import Agent, get_story_id, clear_shared
from sbs_utils.procedural.quest import (QuestState, quest_get, quest_get_state,
                                        quest_add, quest_set_key, document_get_amd_file)
from sbs_utils.procedural.amd_quest import amd_quest_data
from sbs_utils.procedural import quest_driver as QD


ARC = """\
# [The arc](arc)
---
Arc
---

## [Step one](step_one)
---
Job
Scope: shared
Done when: destroy 1 raider
Reward: 5 credits
---

# [An offered job](offered)
---
Job
State: idle
Done when: destroy 2 raiders
Reward: 9 credits
---
"""


OFFERED_ARC = """# [A job on the board](job)
---
Job
Scope: shared
State: idle
Done when: destroy 2 raiders
Reward: 9 credits
---

## [Step one](step_one)
---
Job
Scope: shared
Done when: destroy 1 raider
Reward: 5 credits
---
"""


# NOTE on the fixture: a nested step attaches only when it resolves to the SAME
# holder as its parent - quest_folder needs the parent's node to be on that agent.
# A `scope: shared` Arc with a plain (ship-scoped) Job child therefore grants the
# parent and silently drops the child.


def _doc(src=ARC):
    return document_get_amd_file(None, "d", content=src, data_parser=amd_quest_data)


class Base(unittest.TestCase):
    def setUp(self):
        Agent.clear()
        clear_shared()
        self.agent = Agent()
        self.agent.id = get_story_id()
        self.agent.add()


class TestRegrantKeepsProgress(Base):
    def test_a_progressed_step_under_an_OFFERED_parent_survives(self):
        # The parent must still be OFFERED for this to bite: quest_get_state returns
        # IDLE for "absent" and for "offered" alike, so the old guard re-ran quest_add
        # on the parent - and quest_add builds a fresh node with "children": {}.
        QD.quest_grant_amd(self.agent.id, _doc(OFFERED_ARC))
        QD.quest_mark_active(Agent.SHARED_ID, "job/step_one")
        self.assertEqual(quest_get_state(Agent.SHARED_ID, "job"), QuestState.IDLE,
                         "fixture: the parent must still be offered")
        QD.quest_grant_amd(self.agent.id, _doc(OFFERED_ARC))   # Continue / restart
        self.assertEqual(quest_get_state(Agent.SHARED_ID, "job/step_one"),
                         QuestState.ACTIVE,
                         "the re-grant rebuilt the offered parent and dropped the "
                         "progressed step underneath it")

    def test_a_completed_step_is_not_resurrected(self):
        QD.quest_grant_amd(self.agent.id, _doc())
        QD.quest_mark_active(Agent.SHARED_ID, "arc/step_one")
        QD.quest_mark_complete(Agent.SHARED_ID, "arc/step_one")
        QD.quest_grant_amd(self.agent.id, _doc())
        self.assertEqual(quest_get_state(Agent.SHARED_ID, "arc/step_one"),
                         QuestState.COMPLETE)

    def test_an_offered_job_is_not_rebuilt(self):
        QD.quest_grant_amd(self.agent.id, _doc())
        first = quest_get(Agent.SHARED_ID, "offered") or quest_get(self.agent.id, "offered")
        self.assertIsNotNone(first)
        QD.quest_grant_amd(self.agent.id, _doc())
        second = quest_get(Agent.SHARED_ID, "offered") or quest_get(self.agent.id, "offered")
        self.assertIs(second, first, "an offered quest was replaced by a fresh node")

    def test_a_grant_still_creates_what_is_missing(self):
        QD.quest_grant_amd(self.agent.id, _doc())
        self.assertIsNotNone(quest_get(Agent.SHARED_ID, "arc"))
        self.assertIsNotNone(quest_get(Agent.SHARED_ID, "arc/step_one"))


ACTION_DOC = """\
# [The trap closes](ambush)
---
Job
Action: raider_camp probe_fires now
Done when: destroy 1 raider
Reward: 5 credits
---
"""


class TestActionFiresOnTheDriverPaths(Base):
    def setUp(self):
        super().setUp()
        self.ran = []
        from sbs_utils.procedural import amd_action
        self._prev = dict(amd_action._VERBS)
        # A verb of our own: the built-ins refuse re-registration (same loud-collision
        # contract as amd_register_fields), and what is under test is whether the block
        # RUNS at all, not what any particular verb does.
        amd_action.amd_action_register(
            "probe_fires",
            lambda actor, operand, line=None: self.ran.append((actor, operand)),
            domain="test")

    def tearDown(self):
        from sbs_utils.procedural import amd_action
        amd_action._VERBS.clear()
        amd_action._VERBS.update(self._prev)

    def test_quest_mark_active_runs_the_block(self):
        # The Accept button, `Then: reveal`, and a granted-ACTIVE quest all land here.
        QD.quest_grant_amd(self.agent.id, _doc(ACTION_DOC))
        self.ran.clear()
        QD.quest_mark_active(self.agent.id, "ambush")
        self.assertTrue(self.ran, "Action: did not fire on the driver's activation path")

    def test_it_does_not_fire_twice_for_one_activation(self):
        QD.quest_grant_amd(self.agent.id, _doc(ACTION_DOC))
        self.ran.clear()
        QD.quest_mark_active(self.agent.id, "ambush")
        n = len(self.ran)
        QD.quest_mark_active(self.agent.id, "ambush")   # idempotent guard
        self.assertEqual(len(self.ran), n)


class TestOnSignalSeesEveryHolder(Base):
    def test_a_station_held_quest_advances(self):
        # A station is a quest holder that `[SHARED] + players` never looked at.
        station = Agent()
        station.id = get_story_id()
        station.add()
        quest_add(station.id, "resupply", "Resupply", "d",
                  state=QuestState.ACTIVE,
                  data={"on_signal": {"name": "convoy_arrived"}})
        QD.quest_on_signal("convoy_arrived")
        self.assertEqual(quest_get_state(station.id, "resupply"), QuestState.COMPLETE,
                         "a quest held by a station never heard the signal")

    def test_a_player_held_quest_still_advances(self):
        self.agent.add_role("__player__")   # or this is just a second station
        quest_add(self.agent.id, "patrol", "Patrol", "d",
                  state=QuestState.ACTIVE,
                  data={"on_signal": {"name": "sector_clear"}})
        QD.quest_on_signal("sector_clear")
        self.assertEqual(quest_get_state(self.agent.id, "patrol"), QuestState.COMPLETE)

    def test_an_unrelated_signal_changes_nothing(self):
        quest_add(self.agent.id, "patrol", "Patrol", "d",
                  state=QuestState.ACTIVE,
                  data={"on_signal": {"name": "sector_clear"}})
        QD.quest_on_signal("something_else")
        self.assertEqual(quest_get_state(self.agent.id, "patrol"), QuestState.ACTIVE)


if __name__ == "__main__":
    unittest.main()
