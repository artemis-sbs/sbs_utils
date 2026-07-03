"""Standby (engine-network culling by player proximity) - extracted from the
Open Universe into sbs_utils.procedural.standby. Parks objects with no player
within radius, retrieves them when a player comes near."""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()
import unittest
import cosmos_dev.mock.sbs as sbs
from tests.reset_helper import reset_mock
from sbs_utils.procedural.spawn import npc_spawn, player_spawn
from sbs_utils.procedural.query import to_object, to_id, to_object_list
from sbs_utils.procedural.roles import role
import sbs_utils.procedural.standby as standby


def _npc(x, name):
    # spawn returns SpawnData; standby operates on real Agents (role sets)
    return to_object(to_id(npc_spawn(x, 0, 0, name, "raider",
                                     "tsn_light_cruiser", "behav_npcship")))


class TestStandbyCull(unittest.TestCase):
    def setUp(self):
        self.sim = reset_mock(sbs)
        standby._parked_pos.clear()      # process-singleton state; reset per test
        standby._parked_fleets.clear()
        player_spawn(0, 0, 0, "P", "tsn", "tsn_light_cruiser")  # auto-tags __player__

    def test_parks_far_keeps_near(self):
        near = _npc(500, "near")
        far = _npc(100000, "far")
        standby.standby_cull_step([near, far], 1000)
        self.assertNotIn(near.id, standby._parked_pos)   # near a player -> stays
        self.assertIn(far.id, standby._parked_pos)        # far -> parked
        self.assertEqual(standby.standby_cull_count(), 1)

    def test_no_players_is_noop(self):
        for pl in to_object_list(role("__player__")):
            pl.remove_role("__player__")
        far = _npc(100000, "far")
        standby.standby_cull_step([far], 1000)
        self.assertEqual(standby.standby_cull_count(), 0)   # nothing parks w/o players

    def test_clear_retrieves_all(self):
        far = _npc(100000, "far")
        standby.standby_cull_step([far], 1000)
        self.assertEqual(standby.standby_cull_count(), 1)
        standby.standby_cull_clear()
        self.assertEqual(standby.standby_cull_count(), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
