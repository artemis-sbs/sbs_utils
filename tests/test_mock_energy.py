"""
Mock player-energy model tests.

The engine seeds player ships with a full energy tank + an APU that trickles it
back up (neither is in shipData). Flight (impulse + warp) spends energy; firing or
loading torpedoes does NOT (that's the weapons console's energy<->torp conversion,
a separate manual choice). Docking refills it (LM docking, capped at the tank max).
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest
import cosmos_dev.mock.sbs as sbs
from tests.reset_helper import reset_mock


class TestMockEnergy(unittest.TestCase):
    def setUp(self):
        self.sim = reset_mock(sbs)

    def _player(self):
        pid = self.sim.create_space_object("behav_playership", "tsn_light_cruiser", 0x20)
        p = self.sim.space_objects[pid]
        p._pos = sbs.vec3(0, 0, 0)
        return pid, p

    def test_player_spawns_with_full_energy(self):
        # Engine default: a player starts with a FULL tank, not the data_set 0,
        # plus an APU (Cosmos has passive regen, unlike old Artemis).
        _pid, p = self._player()
        self.assertEqual(p.data_set.get("energy"), sbs.PLAYER_ENERGY_MAX)
        self.assertEqual(p.data_set.get("ship_apu_ceiling"), sbs.PLAYER_ENERGY_MAX)
        self.assertGreater(p.data_set.get("ship_apu_output") or 0.0, 0.0)

    def test_npc_does_not_get_a_player_energy_tank(self):
        nid = self.sim.create_space_object("behav_npcship", "tsn_light_cruiser", 0x10)
        n = self.sim.space_objects[nid]
        self.assertNotEqual(n.data_set.get("energy") or 0.0, sbs.PLAYER_ENERGY_MAX)
        self.assertEqual(n.data_set.get("ship_apu_ceiling") or 0.0, 0.0)

    def test_firing_homing_does_not_cost_energy(self):
        pid, p = self._player()
        ds = p.data_set
        ds.set("torpedo_tube_count", 1, 0)
        ds.set("torpedo_types_available", "Homing,Nuke,EMP,Mine", 0)
        ds.set("Homing_NUM", 5, 0); ds.set("Homing_VAL", 5, 0)
        ds.set("torpedo_launch_max_range", 5000.0, 0)
        eid = self.sim.create_space_object("behav_npcship", "tsn_light_cruiser", 0x10)
        self.sim.space_objects[eid]._pos = sbs.vec3(0, 0, 1000)
        ds.set("weapon_target_UID", eid, 0)
        ds.set("playerThrottle", 0.0, 0)            # idle: isolate firing from flight drain

        sbs.resume_sim()
        for _ in range(150):                         # 5s: fires at least one homing
            sbs.physics_tick(dt=1 / 30)
        self.assertLess(ds.get("Homing_NUM"), 5)     # a torp was fired
        self.assertEqual(round(ds.get("energy"), 1), sbs.PLAYER_ENERGY_MAX)   # no cost

    def test_warp_drains_energy(self):
        pid, p = self._player()
        ds = p.data_set
        ds.set("playerThrottle", 3.0, 0)             # warp
        sbs.resume_sim()
        for _ in range(int(30 * 30)):                # 30 sim-seconds
            sbs.physics_tick(dt=1 / 30)
        self.assertLess(ds.get("energy"), sbs.PLAYER_ENERGY_MAX - 50)   # noticeably drained

    def test_apu_recharges_when_idle(self):
        pid, p = self._player()
        ds = p.data_set
        ds.set("energy", 400.0, 0)                   # partly drained
        ds.set("playerThrottle", 0.0, 0)             # idle -> APU should refill
        sbs.resume_sim()
        for _ in range(int(30 * 30)):
            sbs.physics_tick(dt=1 / 30)
        self.assertGreater(ds.get("energy"), 400.0)
        self.assertLessEqual(ds.get("energy"), sbs.PLAYER_ENERGY_MAX)   # never exceeds ceiling

    def test_impulse_costs_less_than_warp(self):
        # Same duration: impulse (thr 1) should spend far less than warp (thr 3).
        _pa, pa = self._player()
        pa.data_set.set("playerThrottle", 1.0, 0)
        nid = self.sim.create_space_object("behav_playership", "tsn_light_cruiser", 0x20)
        pb = self.sim.space_objects[nid]; pb._pos = sbs.vec3(9e5, 0, 0)
        pb.data_set.set("playerThrottle", 3.0, 0)
        sbs.resume_sim()
        for _ in range(int(20 * 30)):
            sbs.physics_tick(dt=1 / 30)
        impulse_spent = sbs.PLAYER_ENERGY_MAX - pa.data_set.get("energy")
        warp_spent = sbs.PLAYER_ENERGY_MAX - pb.data_set.get("energy")
        self.assertLess(impulse_spent, warp_spent)


if __name__ == '__main__':
    unittest.main()
