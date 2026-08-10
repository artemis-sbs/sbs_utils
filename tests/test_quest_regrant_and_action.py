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


POSTED_DOC = """# [Posted on the board](posted)
---
Job
At start: posting
Done when: destroy 1 raider
---
"""


class TestPostingIsARealState(Base):
    """`At start: posting` was an authored enum value with no entry in _STATE_NAMES,
    so it parsed, passed lint, and silently granted IDLE - i.e. it looked like it
    worked and produced an ordinary acceptable job.

    The state it should have granted is the one this feature needs: LISTED, but not
    button-acceptable (`quest_tab_controls_gate` shows Accept only for IDLE). A board
    posting you take by answering the call, not by pressing Accept.
    """

    def test_it_grants_POSTING_not_IDLE(self):
        QD.quest_grant_amd(self.agent.id, _doc(POSTED_DOC))
        self.assertEqual(quest_get_state(self.agent.id, "posted"), QuestState.POSTING)

    def test_a_posted_quest_is_not_button_acceptable(self):
        QD.quest_grant_amd(self.agent.id, _doc(POSTED_DOC))
        item = {"agent_id": self.agent.id, "key": "posted",
                "state": int(QuestState.POSTING)}
        gate = QD.quest_tab_controls_gate("comms", item, "comms", False, "comms")
        self.assertFalse(gate.get("show_accept"))
        # ...and the same console DOES offer Accept for an ordinary available job,
        # so this is the state talking and not the console gate.
        item["state"] = int(QuestState.IDLE)
        self.assertTrue(QD.quest_tab_controls_gate(
            "comms", item, "comms", False, "comms").get("show_accept"))

    def test_it_can_still_be_activated(self):
        QD.quest_grant_amd(self.agent.id, _doc(POSTED_DOC))
        QD.quest_mark_active(self.agent.id, "posted")
        self.assertEqual(quest_get_state(self.agent.id, "posted"), QuestState.ACTIVE)


CHAIN_DOC = """# [First](first)
---
Job
Done when: signal one_done
Then: signal act_two
---

# [Second](second)
---
Job
Done when: signal act_two
---
"""


class TestThenSignalIsAQuestMilestone(Base):
    """`Then: signal X` emitted only the RAW signal, so one quest's completion could
    not drive another quest's `Done when: signal X` - which is exactly what the two
    lines read as if they do. Both spellings go out now: the raw one so a `//signal/X`
    route still matches what the author wrote, and the normalized `quest_signal` the
    driver actually compares against.
    """

    def _complete_first(self):
        """Complete `first` and return every (signal, data) it emitted.

        `quest_on_signal` is driven by a MAST route (`//shared/signal/quest_signal`),
        not by the library, so what the library controls - and all this can assert
        directly - is what goes OUT.
        """
        seen = []
        from sbs_utils.procedural import quest_driver as _qd
        real = _qd.signal_emit
        _qd.signal_emit = lambda name, data=None: (seen.append((name, data or {})),
                                                   real(name, data))[1]
        try:
            QD.quest_grant_amd(self.agent.id, _doc(CHAIN_DOC))
            QD.quest_mark_active(self.agent.id, "first")
            QD.quest_mark_active(self.agent.id, "second")
            QD.quest_mark_complete(self.agent.id, "first")
        finally:
            _qd.signal_emit = real
        return seen

    def test_it_emits_a_quest_milestone_carrying_the_name(self):
        milestones = [d.get("SIGNAL_NAME") for name, d in self._complete_first()
                      if name == "quest_signal"]
        self.assertIn("act_two", milestones,
                      "Then: signal never reached the quest signal bus")

    def test_the_raw_signal_still_goes_out(self):
        # A `//signal/act_two` route matches what the author WROTE, so the raw emit
        # cannot be replaced by the normalized one.
        self.assertIn("act_two", [n for n, _ in self._complete_first()])

    def test_the_milestone_completes_the_quest_waiting_on_it(self):
        # The route's half, run by hand: this is what LM's //shared/signal/quest_signal
        # does with the payload above.
        self._complete_first()
        QD.quest_on_signal("act_two")
        self.assertEqual(quest_get_state(self.agent.id, "second"), QuestState.COMPLETE)


ACTOR_DOC = """# [Beat](beat)
---
Job
Action: anyone notes_actor
---
"""


class TestTheHolderIsSelf(Base):
    """A quest `Action:` block runs with the HOLDER as its actor.

    Without it `self` resolved to nothing in a quest (it only ever worked in an urge),
    and a verb could not tell a beat held by ONE player ship from one held by the
    shared story agent - which is the whole audience question for `X hails Y`.
    """

    def setUp(self):
        super().setUp()
        self.seen = []
        from sbs_utils.procedural import amd_action
        self._prev = dict(amd_action._VERBS)
        amd_action.amd_action_register(
            "notes_actor",
            lambda actor, operand, line=None: self.seen.append(amd_action.amd_action_actor()),
            operand="none", domain="test")

    def tearDown(self):
        from sbs_utils.procedural import amd_action
        amd_action._VERBS.clear()
        amd_action._VERBS.update(self._prev)

    def test_the_actor_is_the_quest_holder(self):
        QD.quest_grant_amd(self.agent.id, _doc(ACTOR_DOC))
        self.seen.clear()
        QD.quest_mark_active(self.agent.id, "beat")
        self.assertEqual(self.seen, [self.agent.id])

    def test_the_actor_is_restored_afterwards(self):
        from sbs_utils.procedural import amd_action
        QD.quest_grant_amd(self.agent.id, _doc(ACTOR_DOC))
        QD.quest_mark_active(self.agent.id, "beat")
        self.assertIsNone(amd_action.amd_action_actor())


if __name__ == "__main__":
    unittest.main()
