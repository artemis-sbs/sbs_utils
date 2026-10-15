"""`Done when: destroy X by players` counts only a kill by a player ship or its craft.

A game-level kill goal counts ANY kill, so in a Siege the Corsair Queen's Badb was sunk
by BioMechs and "Sink the Badb" completed for a crew that never fired (seen in the
engine, author course c2-10). `by players` is the opt-in; without it nothing changes.

    python -m unittest tests.test_quest_kill_by_players
"""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import sbs_utils.mast_sbs.story_nodes  # noqa: F401  import first to break a circular import
from cosmos_dev.mock import sbs as sbs
from tests.reset_helper import reset_mock
from sbs_utils.agent import Agent
from sbs_utils.procedural.quest import quest_get_state, QuestState
from sbs_utils.procedural.a2x.spawn import create_enemy
from sbs_utils.procedural.spawn import player_spawn
from sbs_utils.procedural.query import to_id
from sbs_utils.procedural.amd_quest import amd_trigger
from sbs_utils.procedural import quest_driver as QD

SH = Agent.SHARED_ID


class KillByPlayers(unittest.TestCase):
    def setUp(self):
        reset_mock(sbs)

    def _grant(self, goal):
        from sbs_utils.procedural.amd_doc import document_get_amd_file
        from sbs_utils.procedural.amd_quest import amd_quest_data
        content = chr(10).join(["# [Sink the Badb](sink)", "---", "Objective",
                                "Done when: " + goal, "---", "prose", ""])
        QD.quest_grant_amd(SH, document_get_amd_file(None, content=content,
                                                     data_parser=amd_quest_data))

    def _ship(self, name, roles):
        sid = to_id(create_enemy(0, 0, 0, "kralien_cruiser", name=name))
        for r in roles:
            Agent.get(sid).add_role(r)
        return sid

    def _player(self):
        return to_id(player_spawn(100, 0, 0, "Artemis", "tsn", "tsn_battle_cruiser"))

    def _state(self):
        return int(quest_get_state(SH, "sink"))

    def test_the_words_parse_and_leave_the_target_alone(self):
        trig, data = amd_trigger("destroy the badb by players")
        self.assertEqual(trig, "on_kill")
        self.assertTrue(data.get("by_players"))
        self.assertEqual(amd_trigger("destroy the badb")[1].get("role"), data.get("role"))
        self.assertTrue(amd_trigger("destroy 3 raiders by the players")[1].get("by_players"))
        self.assertNotIn("by_players", amd_trigger("destroy 3 raiders")[1])

    def test_a_third_party_kill_does_not_count(self):
        self._grant("destroy badb by players")
        badb = self._ship("Badb", ["badb"])
        biomech = self._ship("BioMech", ["biomech"])
        QD.quest_on_kill_shared(badb, biomech, 0)
        self.assertEqual(self._state(), int(QuestState.ACTIVE))

    def test_a_player_kill_counts(self):
        self._grant("destroy badb by players")
        QD.quest_on_kill_shared(self._ship("Badb", ["badb"]), self._player(), 0)
        self.assertEqual(self._state(), int(QuestState.COMPLETE))

    def test_a_kill_by_a_players_fighter_counts(self):
        self._grant("destroy badb by players")
        fighter = self._ship("Fighter", ["fighter"])
        QD.quest_on_kill_shared(self._ship("Badb", ["badb"]), fighter, self._player())
        self.assertEqual(self._state(), int(QuestState.COMPLETE))

    def test_without_the_words_any_kill_still_counts(self):
        self._grant("destroy badb")
        QD.quest_on_kill_shared(self._ship("Badb", ["badb"]), self._ship("X", ["biomech"]), 0)
        self.assertEqual(self._state(), int(QuestState.COMPLETE))

    def test_an_old_caller_that_names_no_killer_still_counts(self):
        self._grant("destroy badb by players")
        QD.quest_on_kill_shared(self._ship("Badb", ["badb"]))
        self.assertEqual(self._state(), int(QuestState.COMPLETE))


if __name__ == "__main__":
    unittest.main()
