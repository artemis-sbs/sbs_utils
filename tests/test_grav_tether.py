"""grav_tether primitive — registry / enforcer / reel logic against the mock.

The PULL physics is engine-native and engine-verified (the mock stores connections but
doesn't simulate the pull), so these tests cover the Python we own: mode presets, the
impulse-only enforcement (cap / snap / off), the reel ramp, and dead-object self-heal.
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest

from cosmos_dev.mock import sbs
from tests.reset_helper import reset_mock
from sbs_utils.procedural.query import to_id, to_object, get_data_set_value
from sbs_utils.procedural.spawn import player_spawn, npc_spawn
from sbs_utils.procedural import grav_tether as gt


class TestGravTether(unittest.TestCase):
    def setUp(self):
        reset_mock(sbs)
        gt.grav_tether_clear_all()
        gt.grav_tether_set_overspeed_default(gt.OVERSPEED_CAP)
        self.ship = to_id(player_spawn(0, 0, 0, "Tug", "tsn", "tsn_light_cruiser"))
        self.load = to_id(npc_spawn(2000, 0, 0, "Load", "tsn", "tsn_light_cruiser", "behav_npcship"))

    def tearDown(self):
        gt.grav_tether_clear_all()

    def _warp(self):
        to_object(self.ship).data_set.set("playerThrottle", 3.0)

    # --- attach / get / release ---------------------------------------------

    def test_attach_creates_connection(self):
        con = gt.grav_tether_attach(self.ship, self.load, pull_distance=500, stiffness=5)
        self.assertIsNotNone(con)
        self.assertIsNotNone(gt.grav_tether_get(self.ship, self.load))
        self.assertEqual(con.offset, 5.0)

    def test_attach_missing_object_returns_none(self):
        self.assertIsNone(gt.grav_tether_attach(self.ship, 0))

    def test_release_removes_it(self):
        gt.grav_tether_tow(self.ship, self.load, 500)
        gt.grav_tether_release(self.ship, self.load)
        self.assertIsNone(gt.grav_tether_get(self.ship, self.load))
        self.assertNotIn((self.ship, self.load), gt._TETHERS)

    def test_release_all_drops_every_tether_from_source(self):
        load2 = to_id(npc_spawn(0, 0, 3000, "L2", "tsn", "tsn_light_cruiser", "behav_npcship"))
        gt.grav_tether_tow(self.ship, self.load, 500)
        gt.grav_tether_tow(self.ship, load2, 500)
        gt.grav_tether_release_all(self.ship)
        self.assertEqual([k for k in gt._TETHERS if k[0] == self.ship], [])

    # --- mode presets --------------------------------------------------------

    def test_lock_is_rigid(self):
        con = gt.grav_tether_lock(self.ship, self.load)
        self.assertEqual(con.offset, 0.0)
        self.assertEqual(gt._TETHERS[(self.ship, self.load)]["pull"], 0.0)

    def test_tow_sets_stiffness_and_pull(self):
        con = gt.grav_tether_tow(self.ship, self.load, 600)
        self.assertEqual(con.offset, gt.DEFAULT_TOW_STIFFNESS)
        self.assertEqual(gt._TETHERS[(self.ship, self.load)]["pull"], 600.0)

    def test_tow_is_a_rope_hold_not_static_reel_in(self):
        # Engine data: a static tether reels the load fully in, so Tow uses the toggle.
        gt.grav_tether_tow(self.ship, self.load, 600)   # load @2000 > 600 -> taut
        self.assertTrue(gt._TETHERS[(self.ship, self.load)].get("rope"))
        self.assertIsNotNone(gt.grav_tether_get(self.ship, self.load))
        # inside the rope -> released (a static tow would keep pulling it in)
        to_object(self.load).pos = sbs.vec3(300, 0, 0)   # dist 300 < 600
        gt.grav_tether_tick()
        self.assertIsNone(gt.grav_tether_get(self.ship, self.load))
        self.assertIn((self.ship, self.load), gt._TETHERS)   # still managed

    # --- impulse-only enforcement -------------------------------------------

    def test_cap_clamps_throttle_and_keeps_tether(self):
        gt.grav_tether_tow(self.ship, self.load, 500, overspeed=gt.OVERSPEED_CAP)
        self._warp()
        gt.grav_tether_tick()
        self.assertEqual(get_data_set_value(self.ship, "playerThrottle"), 1.0)
        self.assertIsNotNone(gt.grav_tether_get(self.ship, self.load))

    def test_snap_breaks_tether_at_warp(self):
        gt.grav_tether_tow(self.ship, self.load, 500, overspeed=gt.OVERSPEED_SNAP)
        self._warp()
        gt.grav_tether_tick()
        self.assertIsNone(gt.grav_tether_get(self.ship, self.load))
        self.assertNotIn((self.ship, self.load), gt._TETHERS)

    def test_off_leaves_throttle_alone(self):
        gt.grav_tether_tow(self.ship, self.load, 500, overspeed=gt.OVERSPEED_OFF)
        self._warp()
        gt.grav_tether_tick()
        self.assertEqual(get_data_set_value(self.ship, "playerThrottle"), 3.0)
        self.assertIsNotNone(gt.grav_tether_get(self.ship, self.load))

    def test_impulse_speed_is_not_capped(self):
        gt.grav_tether_tow(self.ship, self.load, 500)
        to_object(self.ship).data_set.set("playerThrottle", 1.0)
        gt.grav_tether_tick()
        self.assertEqual(get_data_set_value(self.ship, "playerThrottle"), 1.0)

    def test_overspeed_default_applies_when_unspecified(self):
        gt.grav_tether_set_overspeed_default(gt.OVERSPEED_SNAP)
        gt.grav_tether_tow(self.ship, self.load, 500)   # no explicit overspeed
        self._warp()
        gt.grav_tether_tick()
        self.assertIsNone(gt.grav_tether_get(self.ship, self.load))

    # --- reel ----------------------------------------------------------------

    def test_reel_ramps_rope_to_zero(self):
        gt.grav_tether_reel(self.ship, self.load, rate=500)
        self.assertGreater(gt._TETHERS[(self.ship, self.load)]["pull"], 0.0)  # ~2000 sep
        for _ in range(20):
            st = gt._TETHERS.get((self.ship, self.load))
            if st is None or st["pull"] <= 0.0:
                break
            gt.grav_tether_tick()
        st = gt._TETHERS[(self.ship, self.load)]
        self.assertEqual(st["pull"], 0.0)
        self.assertEqual(st["reel_rate"], 0.0)

    # --- swing (rope-toggle) -------------------------------------------------

    def test_swing_taut_engages_slack_releases(self):
        # anchor = load @ (2000,0,0); ship (player) starts @ 0 -> dist 2000 > rope 800.
        gt.grav_tether_swing(self.load, self.ship, 800)
        self.assertIsNotNone(gt.grav_tether_get(self.load, self.ship))   # taut -> engaged
        # fly inside the rope: dist 500 < 800 -> slack, released
        to_object(self.ship).pos = sbs.vec3(1500, 0, 0)
        gt.grav_tether_tick()
        self.assertIsNone(gt.grav_tether_get(self.load, self.ship))      # slack -> free
        # swing back out past the rope -> re-engages
        to_object(self.ship).pos = sbs.vec3(0, 0, 0)
        gt.grav_tether_tick()
        self.assertIsNotNone(gt.grav_tether_get(self.load, self.ship))   # taut again
        # the tether stays registered/managed across engage/release
        self.assertIn((self.load, self.ship), gt._TETHERS)

    def test_swing_release_clears_registry(self):
        gt.grav_tether_swing(self.load, self.ship, 800)
        gt.grav_tether_release(self.load, self.ship)
        self.assertNotIn((self.load, self.ship), gt._TETHERS)
        self.assertIsNone(gt.grav_tether_get(self.load, self.ship))

    # --- mock physics simulation ---------------------------------------------

    def _sep(self):
        import math
        s = to_object(self.ship).pos
        l = to_object(self.load).pos
        return math.dist((s.x, s.y, s.z), (l.x, l.y, l.z))

    def test_mock_physics_pulls_the_target(self):
        # The mock now simulates the pull (calibrated to engine data), so a live
        # connection actually moves the target during physics_tick.
        d0 = self._sep()                              # 2000
        gt.grav_tether_lock(self.ship, self.load)     # offset 0 -> rigid snap
        sbs.sim._paused = False
        sbs.physics_tick(0.1)
        self.assertLess(self._sep(), d0 - 500)        # target reeled toward the source

    def test_mock_physics_no_move_without_connection(self):
        d0 = self._sep()
        sbs.sim._paused = False
        sbs.physics_tick(0.1)
        self.assertAlmostEqual(self._sep(), d0, delta=1.0)   # nothing pulls it

    # --- self-heal -----------------------------------------------------------

    def test_dead_target_self_heals(self):
        gt.grav_tether_tow(self.ship, self.load, 500)
        sbs.delete_object(self.load)
        gt.grav_tether_tick()
        self.assertNotIn((self.ship, self.load), gt._TETHERS)


if __name__ == "__main__":
    unittest.main()
