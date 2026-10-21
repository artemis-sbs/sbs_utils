"""A ship stops shooting at a side it is no longer hostile to.

Seen in the engine (2026-10-21, OU C5-03): after Negotiate Ceasefire the Gleaners' fleet
turned neutral on every display and kept firing until the player ship died. The fleet
brains already chose no NEW target - a ceasefired side is not an enemy - but nothing
cleared the weapons target each ship already held, and the engine fires at whatever
`target_id` names. side_stand_down clears it; LM's ai_fleet_init_blackboard calls it on
every tick.

    python -m unittest tests.test_side_stand_down
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest

import sbs_utils.mast_sbs.story_nodes  # noqa: F401  import first (circular import)
from cosmos_dev.mock import sbs as sbs
from tests.reset_helper import reset_mock

from sbs_utils.procedural.a2x.spawn import create_enemy
from sbs_utils.procedural.query import to_id, to_object
from sbs_utils.procedural.roles import add_role
from sbs_utils.procedural.sides import side_ensure, side_set_relations, side_stand_down
from sbs_utils.procedural.space_objects import target


class StandDown(unittest.TestCase):
    def setUp(self):
        reset_mock(sbs)
        side_ensure("tsn", "TSN")
        side_ensure("gleaners", "The Gleaners")
        side_ensure("monster", "Monster")
        side_set_relations("tsn", "gleaners", sbs.DIPLOMACY.HOSTILE)
        self.player = to_id(create_enemy(0, 0, 0, "tsn_light_cruiser", name="Artemis", side="tsn"))
        add_role(self.player, "__player__")
        self.raider = to_id(create_enemy(900, 0, 0, "torgoth_destroyer", name="G1", side="gleaners"))
        self.beast = to_id(create_enemy(900, 0, 900, "torgoth_destroyer", name="M1", side="monster"))
        target(self.raider, self.player)
        target(self.beast, self.player)

    def _target_of(self, ship):
        return to_object(ship).data_set.get("target_id", 0)

    def test_still_hostile_keeps_its_target(self):
        self.assertEqual(side_stand_down([self.raider]), [])
        self.assertEqual(self._target_of(self.raider), self.player)

    def test_a_ceasefire_clears_the_target(self):
        side_set_relations("tsn", "gleaners", sbs.DIPLOMACY.NEUTRAL)
        self.assertEqual(side_stand_down([self.raider]), [self.raider])
        self.assertEqual(self._target_of(self.raider), 0)

    def test_an_alliance_clears_it_too(self):
        side_set_relations("tsn", "gleaners", sbs.DIPLOMACY.ALLIED)
        self.assertEqual(side_stand_down([self.raider]), [self.raider])

    def test_a_side_with_no_relations_is_left_alone(self):
        # Feral monsters have no diplomacy at all: UNKNOWN is not a truce.
        self.assertEqual(side_stand_down([self.beast]), [])
        self.assertEqual(self._target_of(self.beast), self.player)

    def test_no_target_is_nothing_to_do(self):
        quiet = to_id(create_enemy(0, 0, 900, "torgoth_destroyer", name="G2", side="gleaners"))
        side_set_relations("tsn", "gleaners", sbs.DIPLOMACY.NEUTRAL)
        self.assertEqual(side_stand_down([quiet]), [])


if __name__ == "__main__":
    unittest.main()
