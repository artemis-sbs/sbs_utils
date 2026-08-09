"""One counter instead of a walk, and the walk it replaces.

quest_tab_state_sig is driven by an `on change` in quest_tab.mast, so it ran EVERY
FRAME on every console with the Quests tab open - walking three quest trees and
building a join-string of every node, including COMPLETE, FAILED and SECRET ones.
It scaled with TOTAL nodes, not active ones: Peacetime Remastered grants 33 nodes
per player ship, so eight ships is ~270 nodes rebuilt per console per frame.

The four tick functions had the same shape once per 2 sim-seconds: each called
_active_quests per holder, and each of those walked the whole tree again.

The correctness question for all of it is the same one - does the number change
whenever a tree does? - so that is most of what this file asserts.
"""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

from sbs_utils.agent import Agent, get_story_id, clear_shared
from sbs_utils.procedural.quest import (QuestState, quest_add, quest_remove,
                                        quest_set_key, quest_transfer,
                                        quest_generation, quest_get_state)
from sbs_utils.procedural import quest_driver as QD


class GenBase(unittest.TestCase):
    def setUp(self):
        Agent.clear()
        clear_shared()

    def _agent(self):
        a = Agent()
        a.id = get_story_id()
        a.add()
        return a


class TestTheCounterMoves(GenBase):
    def test_add(self):
        g = quest_generation()
        quest_add(Agent.SHARED_ID, "q", "Q", "d")
        self.assertGreater(quest_generation(), g)

    def test_state_write(self):
        quest_add(Agent.SHARED_ID, "q", "Q", "d")
        g = quest_generation()
        quest_set_key(Agent.SHARED_ID, "q", "state", QuestState.ACTIVE)
        self.assertGreater(quest_generation(), g)

    def test_remove(self):
        quest_add(Agent.SHARED_ID, "q", "Q", "d")
        g = quest_generation()
        quest_remove(Agent.SHARED_ID, "q")
        self.assertGreater(quest_generation(), g)

    def test_transfer(self):
        ship = self._agent()
        quest_add(ship.id, "q", "Q", "d")
        g = quest_generation()
        quest_transfer(ship.id, Agent.SHARED_ID, "q")
        self.assertGreater(quest_generation(), g)

    def test_a_frame_with_no_change_does_not_move_it(self):
        quest_add(Agent.SHARED_ID, "q", "Q", "d")
        g = quest_generation()
        for _ in range(20):
            quest_get_state(Agent.SHARED_ID, "q")
            QD.quest_tab_state_sig(0, 0)
        self.assertEqual(quest_generation(), g)

    def test_removing_a_quest_that_is_not_there_is_not_a_change(self):
        g = quest_generation()
        quest_remove(Agent.SHARED_ID, "never_existed")
        self.assertEqual(quest_generation(), g)


class TestTheSignature(GenBase):
    def test_it_changes_on_every_kind_of_change(self):
        seen = {QD.quest_tab_state_sig(0, 0)}
        quest_add(Agent.SHARED_ID, "q", "Q", "d")
        seen.add(QD.quest_tab_state_sig(0, 0))
        quest_set_key(Agent.SHARED_ID, "q", "state", QuestState.ACTIVE)
        seen.add(QD.quest_tab_state_sig(0, 0))
        quest_set_key(Agent.SHARED_ID, "q", "state", QuestState.COMPLETE)
        seen.add(QD.quest_tab_state_sig(0, 0))
        quest_remove(Agent.SHARED_ID, "q")
        seen.add(QD.quest_tab_state_sig(0, 0))
        self.assertEqual(len(seen), 5, "a change did not reach the repaint signal")

    def test_a_reveal_is_caught(self):
        # SECRET -> ACTIVE is the case the old walk existed to catch.
        quest_add(Agent.SHARED_ID, "q", "Q", "d", state=QuestState.SECRET)
        before = QD.quest_tab_state_sig(0, 0)
        quest_set_key(Agent.SHARED_ID, "q", "state", QuestState.ACTIVE)
        self.assertNotEqual(QD.quest_tab_state_sig(0, 0), before)

    def test_consoles_do_not_share_a_signature(self):
        a = QD.quest_tab_state_sig(1, 10)
        b = QD.quest_tab_state_sig(2, 20)
        self.assertNotEqual(a, b)

    def test_it_is_stable_between_changes(self):
        quest_add(Agent.SHARED_ID, "q", "Q", "d")
        self.assertEqual(QD.quest_tab_state_sig(3, 4), QD.quest_tab_state_sig(3, 4))


class TestActiveQuestsCache(GenBase):
    def test_the_same_list_is_reused_until_something_changes(self):
        quest_add(Agent.SHARED_ID, "q", "Q", "d", state=QuestState.ACTIVE)
        a = QD._active_quests(Agent.SHARED_ID)
        self.assertIs(QD._active_quests(Agent.SHARED_ID), a)

    def test_a_state_change_invalidates_it(self):
        quest_add(Agent.SHARED_ID, "q", "Q", "d", state=QuestState.ACTIVE)
        a = QD._active_quests(Agent.SHARED_ID)
        self.assertEqual(len(a), 1)
        quest_set_key(Agent.SHARED_ID, "q", "state", QuestState.COMPLETE)
        b = QD._active_quests(Agent.SHARED_ID)
        self.assertIsNot(b, a)
        self.assertEqual(len(b), 0)

    def test_a_new_quest_is_visible_immediately(self):
        QD._active_quests(Agent.SHARED_ID)
        quest_add(Agent.SHARED_ID, "q", "Q", "d", state=QuestState.ACTIVE)
        self.assertEqual([q for q, _d in QD._active_quests(Agent.SHARED_ID)], ["q"])

    def test_nested_arc_steps_still_come_back_by_full_path(self):
        quest_add(Agent.SHARED_ID, "arc", "Arc", "d", state=QuestState.ACTIVE)
        quest_add(Agent.SHARED_ID, "arc/step", "Step", "d", state=QuestState.ACTIVE)
        paths = [q for q, _d in QD._active_quests(Agent.SHARED_ID)]
        self.assertIn("arc/step", paths)

    def test_the_cache_matches_a_brute_force_walk_across_many_edits(self):
        import random
        rng = random.Random(20260809)
        states = [QuestState.IDLE, QuestState.ACTIVE, QuestState.COMPLETE,
                  QuestState.FAILED, QuestState.SECRET]
        for i in range(12):
            quest_add(Agent.SHARED_ID, f"q{i}", f"Q{i}", "d", state=QuestState.IDLE)
        for _ in range(200):
            quest_set_key(Agent.SHARED_ID, f"q{rng.randrange(12)}", "state",
                          rng.choice(states))
            cached = sorted(q for q, _d in QD._active_quests(Agent.SHARED_ID))
            brute = []
            tree = QD.quest_agent_quests(Agent.SHARED_ID)
            QD._collect_active_quests(tree.get("children", {}), "", brute)
            self.assertEqual(cached, sorted(q for q, _d in brute))


class TestAnyHolderState(GenBase):
    def test_it_agrees_with_a_direct_scan(self):
        ship = self._agent()
        quest_add(ship.id, "deliver", "D", "d", state=QuestState.ACTIVE)
        self.assertTrue(QD.quest_any_holder_state("deliver", QuestState.ACTIVE))
        self.assertFalse(QD.quest_any_holder_state("deliver", QuestState.COMPLETE))
        quest_set_key(ship.id, "deliver", "state", QuestState.COMPLETE)
        self.assertFalse(QD.quest_any_holder_state("deliver", QuestState.ACTIVE))
        self.assertTrue(QD.quest_any_holder_state("deliver", QuestState.COMPLETE))

    def test_an_unknown_quest_is_false(self):
        self.assertFalse(QD.quest_any_holder_state("nope", QuestState.ACTIVE))


if __name__ == "__main__":
    unittest.main()
