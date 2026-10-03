"""A quest the whole table shares pays every side that has a player ship, once each.

`Scope: shared` grants a quest to the SHARED story agent, and that agent has no side -
while credits are paid to a SIDE. So a shared quest's `Reward: 500 credits` was skipped,
in silence: every shipped Siege boss objective carried a reward that paid nobody, and a
ship-held quest completing in the same game paid as normal, so nothing looked broken.

Found by writing the first author lesson against it. A crew finishing "Defeat the
Warlord" has no way to tell the 500 credits never arrived.

    python -m unittest tests.test_quest_shared_reward
"""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import sbs_utils.mast_sbs.story_nodes  # import first to break a circular import
from cosmos_dev.mock import sbs as sbs
from tests.reset_helper import reset_mock

from sbs_utils.agent import Agent
from sbs_utils.procedural.a2x.spawn import create_enemy
from sbs_utils.procedural.query import to_id
from sbs_utils.procedural.quest import quest_add, quest_get_state, QuestState
from sbs_utils.procedural import quest_driver as QD
from sbs_utils.procedural.spawn import player_spawn
from sbs_utils.procedural.sides import side_ensure, to_side_id
from sbs_utils.procedural.inventory import get_inventory_value, set_inventory_value

SH = Agent.SHARED_ID


class _Base(unittest.TestCase):
    def setUp(self):
        reset_mock(sbs)
        for key in ("tsn", "ximni", "raider"):
            side_ensure(key)

    def _player(self, name, side):
        return to_id(player_spawn(0, 0, 0, name, side, "tsn_light_cruiser"))

    def _credits(self, side):
        return get_inventory_value(to_side_id(side), "credits", 0)

    def _boss_objective(self, credits=500):
        """What `quest_grant_amd(SHARED, boss_node)` leaves behind for a Siege boss."""
        quest_add(SH, "defeat_warlord", "Defeat the Warlord", "", state=QuestState.ACTIVE,
                  data={"parent": "siege_mission", "required": True,
                        "reward": {"credits": credits}})


class ASharedRewardIsPaidTests(_Base):
    def test_completing_a_shared_quest_pays_the_players_side(self):
        """The production path: the driver completes it, not a direct grant."""
        self._player("Artemis", "tsn")
        self._boss_objective()
        QD.quest_mark_complete(SH, "defeat_warlord")
        self.assertEqual(int(quest_get_state(SH, "defeat_warlord")), int(QuestState.COMPLETE))
        self.assertEqual(self._credits("tsn"), 500)

    def test_a_side_is_paid_once_however_many_ships_it_flies(self):
        self._player("Artemis", "tsn")
        self._player("Intrepid", "tsn")
        self._player("Aegis", "tsn")
        QD.quest_grant_reward(SH, {"credits": 500})
        self.assertEqual(self._credits("tsn"), 500)

    def test_every_side_with_a_player_ship_is_paid_in_full(self):
        """In full, not a share - nobody is handed part of another side's count."""
        self._player("Artemis", "tsn")
        self._player("Horizon", "ximni")
        QD.quest_grant_reward(SH, {"credits": 500})
        self.assertEqual(self._credits("tsn"), 500)
        self.assertEqual(self._credits("ximni"), 500)

    def test_a_side_with_no_player_ship_is_paid_nothing(self):
        self._player("Artemis", "tsn")
        npc = to_id(create_enemy(0, 0, 0, "kralien_cruiser", name="R"))
        Agent.get(npc).side = "raider"
        QD.quest_grant_reward(SH, {"credits": 500})
        self.assertEqual(self._credits("raider"), 0)
        self.assertEqual(self._credits("ximni"), 0)

    def test_completing_it_twice_pays_once(self):
        self._player("Artemis", "tsn")
        self._boss_objective()
        QD.quest_mark_complete(SH, "defeat_warlord")
        QD.quest_mark_complete(SH, "defeat_warlord")
        self.assertEqual(self._credits("tsn"), 500)

    def test_no_player_ship_pays_nobody_and_does_not_raise(self):
        """The map picker, or a sim built before the crew is seated."""
        QD.quest_grant_reward(SH, {"credits": 500})
        self.assertEqual(self._credits("tsn"), 0)


class ASharedPenaltyIsChargedTests(_Base):
    """The mirror, or failing the table's quest would cost nothing at all."""

    def test_each_player_side_is_charged_once(self):
        self._player("Artemis", "tsn")
        self._player("Intrepid", "tsn")
        self._player("Horizon", "ximni")
        set_inventory_value(to_side_id("tsn"), "credits", 300)
        set_inventory_value(to_side_id("ximni"), "credits", 300)
        QD.quest_grant_penalty(SH, {"credits": 200})
        self.assertEqual(self._credits("tsn"), 100)
        self.assertEqual(self._credits("ximni"), 100)

    def test_a_penalty_never_takes_a_side_below_zero(self):
        self._player("Artemis", "tsn")
        set_inventory_value(to_side_id("tsn"), "credits", 50)
        QD.quest_grant_penalty(SH, {"credits": 200})
        self.assertEqual(self._credits("tsn"), 0)


class AShipHeldRewardIsUnchangedTests(_Base):
    def test_a_ship_held_quest_pays_only_that_ships_side(self):
        artemis = self._player("Artemis", "tsn")
        self._player("Horizon", "ximni")
        QD.quest_grant_reward(artemis, {"credits": 500})
        self.assertEqual(self._credits("tsn"), 500)
        self.assertEqual(self._credits("ximni"), 0)


if __name__ == "__main__":
    unittest.main()
