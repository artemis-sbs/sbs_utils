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
from sbs_utils.procedural.sides import side_ensure


class TestGravTether(unittest.TestCase):
    def setUp(self):
        reset_mock(sbs)
        gt.grav_tether_clear_all()
        gt.grav_tether_set_overspeed_default(gt.OVERSPEED_CAP)
        gt.grav_tether_set_attach_policy(None)
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

    def test_involves_and_release_any_cover_both_ends(self):
        # swing makes the SHIP the target (anchor is source) - a one-button toggle must
        # still see it and release it from either end.
        gt.grav_tether_swing(self.load, self.ship, 800)
        self.assertTrue(gt.grav_tether_involves(self.ship))
        self.assertTrue(gt.grav_tether_involves(self.load))
        gt.grav_tether_release_any(self.ship)
        self.assertFalse(gt.grav_tether_involves(self.ship))
        self.assertNotIn((self.load, self.ship), gt._TETHERS)

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

    # --- swing (circle-point orbit) ------------------------------------------

    def test_swing_holds_radius_while_orbiting(self):
        # Drive a swinger tangentially around an anchor; the circle-point swing must hold
        # the radius (~rope_len) instead of spiraling in (the old center-pull did 758->663).
        import math
        from sbs_utils.procedural.space_objects import target_pos
        anchor = to_id(npc_spawn(0, 0, 0, "Anchor", "tsn", "starbase_command", "behav_station"))
        swinger = to_id(npc_spawn(800, 0, 0, "Sw", "tsn", "tsn_light_cruiser", "behav_npcship"))

        def rad():
            a = to_object(anchor).pos
            s = to_object(swinger).pos
            return math.dist((a.x, a.y, a.z), (s.x, s.y, s.z))

        gt.grav_tether_swing(anchor, swinger, 800)
        target_pos(swinger, 800, 0, 9000, 1.0)        # drive tangentially (+Z)
        sbs.sim._paused = False
        radii = []
        for _ in range(60):
            gt.grav_tether_tick()
            sbs.physics_tick(0.1)
            radii.append(rad())
        settled = radii[15:]
        self.assertTrue(all(560 < r < 1040 for r in settled),
                        "radius spiraled: " + str([int(r) for r in settled[::10]]))

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

    # --- nose-aim acquire (forward cone, no raycast in the API) ---------------

    def test_closest_in_front_prefers_target_ahead(self):
        from sbs_utils.procedural.space_objects import closest_in_front
        from sbs_utils.procedural.roles import any_role
        f = to_object(self.ship).engine_object.forward_vector()
        ahead = to_id(npc_spawn(f.x * 1000, f.y * 1000, f.z * 1000,
                                "Ahead", "raider", "tsn_light_cruiser", "behav_npcship"))
        to_id(npc_spawn(-f.x * 400, -f.y * 400, -f.z * 400,
                        "Behind", "raider", "tsn_light_cruiser", "behav_npcship"))
        cd = closest_in_front(self.ship, any_role("raider"), max_dist=5000, cone_deg=45)
        self.assertIsNotNone(cd)
        self.assertEqual(cd.id, ahead)   # ahead wins even though 'Behind' is nearer

    def test_sources_of_lists_the_tetherers(self):
        gt.grav_tether_tow(self.ship, self.load, 500)
        self.assertEqual(gt.grav_tether_sources_of(self.load), [self.ship])
        self.assertEqual(gt.grav_tether_sources_of(self.ship), [])

    def test_targets_of_is_the_mirror_of_sources_of(self):
        gt.grav_tether_tow(self.ship, self.load, 500)
        self.assertEqual(gt.grav_tether_targets_of(self.ship), [self.load])
        self.assertEqual(gt.grav_tether_targets_of(self.load), [])

    # --- what the beam is doing, for a readout --------------------------------

    def test_every_preset_records_which_one_it_was(self):
        # A readout has to be able to SAY what the beam is doing; tow and swing are the
        # same rope-hold to the physics and completely different to a crew.
        for preset, expected in (
            (lambda: gt.grav_tether_lock(self.ship, self.load), gt.MODE_LOCK),
            (lambda: gt.grav_tether_tow(self.ship, self.load, 500), gt.MODE_TOW),
            (lambda: gt.grav_tether_reel(self.ship, self.load), gt.MODE_REEL),
        ):
            gt.grav_tether_clear_all()
            preset()
            self.assertEqual(gt.grav_tether_mode(self.ship, self.load), expected)
        gt.grav_tether_clear_all()
        gt.grav_tether_swing(self.load, self.ship, 800)
        self.assertEqual(gt.grav_tether_mode(self.load, self.ship), gt.MODE_SWING)

    def test_mode_is_none_when_the_pair_is_free(self):
        self.assertIsNone(gt.grav_tether_mode(self.ship, self.load))

    def test_status_says_which_end_we_are_on(self):
        gt.grav_tether_tow(self.ship, self.load, 500)
        st = gt.grav_tether_status(self.ship)
        self.assertEqual(st["partner"], self.load)
        self.assertEqual(st["role"], "source")
        self.assertEqual(st["mode"], gt.MODE_TOW)
        # The load is on the other end of the same beam, and says so.
        st = gt.grav_tether_status(self.load)
        self.assertEqual(st["partner"], self.ship)
        self.assertEqual(st["role"], "target")

    def test_a_swung_ship_reads_as_the_pulled_end(self):
        # The whole reason role is reported: in a swing the FIGHTER is the target, so a
        # readout that assumes "I am the puller" gets it backwards exactly when being
        # tethered matters most.
        gt.grav_tether_swing(self.load, self.ship, 800)
        st = gt.grav_tether_status(self.ship)
        self.assertEqual(st["role"], "target")
        self.assertEqual(st["partner"], self.load)

    def test_status_and_partner_are_empty_when_free(self):
        self.assertIsNone(gt.grav_tether_status(self.ship))
        self.assertEqual(gt.grav_tether_partner(self.ship), 0)
        gt.grav_tether_tow(self.ship, self.load, 500)
        self.assertEqual(gt.grav_tether_partner(self.ship), self.load)
        gt.grav_tether_release_any(self.ship)
        self.assertEqual(gt.grav_tether_partner(self.ship), 0)

    # --- attach policy (ownership veto hook) ---------------------------------

    def test_attach_policy_vetoes_every_entry_point(self):
        # A policy denying any attach that involves self.load blocks lock/tow/swing.
        gt.grav_tether_set_attach_policy(lambda src, tgt: self.load not in (src, tgt))
        self.assertIsNone(gt.grav_tether_lock(self.ship, self.load))         # via attach
        self.assertIsNone(gt.grav_tether_tow(self.ship, self.load, 500))     # via rope
        self.assertIsNone(gt.grav_tether_swing(self.load, self.ship, 800))   # own body
        self.assertIsNone(gt.grav_tether_get(self.ship, self.load))          # nothing opened
        # a permitted pair still attaches
        other = to_id(npc_spawn(0, 0, 3000, "Other", "tsn", "tsn_light_cruiser", "behav_npcship"))
        self.assertIsNotNone(gt.grav_tether_tow(self.ship, other, 500))

    # --- self-heal -----------------------------------------------------------

    def test_dead_target_self_heals(self):
        gt.grav_tether_tow(self.ship, self.load, 500)
        sbs.delete_object(self.load)
        gt.grav_tether_tick()
        self.assertNotIn((self.ship, self.load), gt._TETHERS)

    # --- the rope-toggle blind spot -----------------------------------------

    def test_has_is_true_during_a_tow_when_get_is_not(self):
        """The bug that made the Weapons popup unable to Release mid-tow.

        A Tow deletes the engine connection whenever the load is inside the rope length,
        so `grav_tether_get` reads None for most of a perfectly good tow. Any UI gated on
        `get` offers "Tow" to something already under tow and never offers "Release".
        """
        to_object(self.load).pos = sbs.vec3(400, 0, 0)   # inside a 500 rope
        gt.grav_tether_tow(self.ship, self.load, 500)
        self.assertIsNone(gt.grav_tether_get(self.ship, self.load),
                          "the toggle should have released the connection inside rope_len")
        self.assertTrue(gt.grav_tether_has(self.ship, self.load),
                        "but the tow is live and the registry must say so")
        self.assertTrue(gt.grav_tether_involves(self.load))

    def test_has_is_false_for_an_untethered_pair(self):
        self.assertFalse(gt.grav_tether_has(self.ship, self.load))
        gt.grav_tether_tow(self.ship, self.load, 500)
        gt.grav_tether_release(self.ship, self.load)
        self.assertFalse(gt.grav_tether_has(self.ship, self.load))

    def test_has_is_pair_specific(self):
        other = to_id(npc_spawn(9000, 0, 0, "Other", "tsn", "tsn_light_cruiser", "behav_npcship"))
        gt.grav_tether_tow(self.ship, self.load, 500)
        self.assertTrue(gt.grav_tether_has(self.ship, self.load))
        self.assertFalse(gt.grav_tether_has(self.ship, other))

    # --- coexistence with mounts -------------------------------------------

    def test_clear_all_does_not_unweld_a_mount(self):
        """The engine has ONE tractor pool, and procedural.mount builds connections in it.

        This used to call ClearTractorConnections(), which is global: every turret welded
        to a hull came off, while mount's own bookkeeping went on insisting they were
        attached. Clearing must touch only what this module registered.
        """
        from sbs_utils.procedural import mount as mt
        host = to_id(npc_spawn(0, 0, 5000, "Host", "tsn", "tsn_light_cruiser", "behav_npcship"))
        pod = to_id(npc_spawn(0, 0, 5000, "Pod", "tsn", "tsn_fighter", "behav_station"))
        mt.mount_attach(host, pod, (0, 0, 200))
        gt.grav_tether_tow(self.ship, self.load, 500)

        gt.grav_tether_clear_all()

        self.assertFalse(gt.grav_tether_has(self.ship, self.load), "our own tether goes")
        self.assertIsNotNone(sbs.sim.GetTractorConnection(host, pod),
                             "the mount's weld must survive - it is not a tether")
        self.assertEqual(mt.mount_count(), 1)
        mt.mount_clear_all()

    def test_mount_clear_all_leaves_tethers_alone(self):
        """And the reverse, so the two are genuinely independent."""
        from sbs_utils.procedural import mount as mt
        host = to_id(npc_spawn(0, 0, 5000, "Host", "tsn", "tsn_light_cruiser", "behav_npcship"))
        pod = to_id(npc_spawn(0, 0, 5000, "Pod", "tsn", "tsn_fighter", "behav_station"))
        mt.mount_attach(host, pod, (0, 0, 200))
        gt.grav_tether_tow(self.ship, self.load, 500)

        mt.mount_clear_all()

        self.assertEqual(mt.mount_count(), 0)
        self.assertTrue(gt.grav_tether_has(self.ship, self.load), "the tow must survive")


class TestGravTetherConstraints(unittest.TestCase):
    """Phase 4: what stops the tether being a win button.

    All of it turns on MASS, and the library deliberately ships no numbers - a mission
    installs them. So each test installs its own, and the last one checks that WITHOUT a
    provider every rule reduces to a no-op rather than a wrong guess.
    """

    def setUp(self):
        reset_mock(sbs)
        gt.grav_tether_clear_all()
        gt.grav_tether_set_mass_fn(None)
        gt.grav_tether_set_grab_speed_limit(None)
        gt.grav_tether_set_tow_energy_cost(0.0)
        # modifier_add resolves a SIDE as well as the object, and warns "Side not found"
        # without one - so the drag lands nowhere a query can see it.
        side_ensure("tsn", "TSN")
        self.ship = to_id(player_spawn(0, 0, 0, "Tug", "tsn", "tsn_light_cruiser"))
        self.load = to_id(npc_spawn(400, 0, 0, "Load", "tsn", "tsn_light_cruiser", "behav_npcship"))

    def tearDown(self):
        gt.grav_tether_clear_all()
        gt.grav_tether_set_mass_fn(None)
        gt.grav_tether_set_grab_speed_limit(None)
        gt.grav_tether_set_tow_energy_cost(0.0)
        # Modifiers outlive reset_mock, so a drag left on a ship by one test is still
        # in the registry for the next one.
        gt._release_drag(self.ship)
        gt._release_drag(self.load)

    def _masses(self, table):
        gt.grav_tether_set_mass_fn(lambda oid: table.get(oid, 1.0))

    def _has_drag(self, obj, key="impulse_upgrade_coeff"):
        """Whether the tow drag is on this object.

        NOT modifier_exists: that does `id in mod.id` with mod.id an int, so it raises
        TypeError on any normal single-target modifier.
        """
        from sbs_utils.procedural.modifiers import modifiers_get_for_object
        return any(m.source == gt._DRAG_KEY
                   for m in (modifiers_get_for_object(obj, key) or []))

    # --- mass ---------------------------------------------------------------

    def test_no_provider_means_evenly_matched(self):
        # The library must not guess. Without a table every rule is inert.
        self.assertEqual(gt.grav_tether_mass(self.ship), gt.DEFAULT_MASS)
        self.assertEqual(gt.grav_tether_mass_ratio(self.ship, self.load), 1.0)

    def test_ratio_reads_both_ends(self):
        self._masses({self.ship: 4.0, self.load: 12.0})
        self.assertEqual(gt.grav_tether_mass_ratio(self.ship, self.load), 3.0)
        self.assertEqual(gt.grav_tether_mass_ratio(self.load, self.ship), 1.0 / 3.0)

    def test_a_broken_provider_falls_back_rather_than_raising(self):
        gt.grav_tether_set_mass_fn(lambda oid: 1 / 0)
        self.assertEqual(gt.grav_tether_mass(self.ship), gt.DEFAULT_MASS)

    # --- who tows whom ------------------------------------------------------

    def test_a_heavier_load_tows_YOU(self):
        """Grab a starbase in a cruiser and the engine pulls the other way.

        The registry key stays as the CALLER wrote it - release/has still work in their
        terms - but the engine pair is flipped so the heavy end holds station.
        """
        self._masses({self.ship: 3.0, self.load: 200.0})
        gt.grav_tether_lock(self.ship, self.load)
        self.assertTrue(gt.grav_tether_has(self.ship, self.load), "caller's view is unchanged")
        self.assertIsNotNone(sbs.sim.GetTractorConnection(self.load, self.ship),
                             "the heavy end must be the one doing the pulling")
        self.assertIsNone(sbs.sim.GetTractorConnection(self.ship, self.load))

    def test_a_lighter_load_is_pulled_normally(self):
        self._masses({self.ship: 8.0, self.load: 1.0})
        gt.grav_tether_lock(self.ship, self.load)
        self.assertIsNotNone(sbs.sim.GetTractorConnection(self.ship, self.load))

    def test_releasing_a_reversed_tether_really_lets_go(self):
        # The bug this guards: deleting only the pair the caller knows about leaves the
        # real (flipped) connection live and the load still held.
        self._masses({self.ship: 3.0, self.load: 200.0})
        gt.grav_tether_lock(self.ship, self.load)
        gt.grav_tether_release(self.ship, self.load)
        self.assertIsNone(sbs.sim.GetTractorConnection(self.load, self.ship))
        self.assertFalse(gt.grav_tether_has(self.ship, self.load))

    # --- tug of war ---------------------------------------------------------

    def test_towing_costs_the_puller_drive(self):
        self._masses({self.ship: 4.0, self.load: 4.0})
        gt.grav_tether_tow(self.ship, self.load, 500)
        gt.grav_tether_tick()
        self.assertTrue(self._has_drag(self.ship, "impulse_upgrade_coeff"))
        self.assertTrue(self._has_drag(self.ship, "turn_upgrade_coeff"))

    def test_a_swing_does_not_slow_the_anchor(self):
        # The anchor is usually a rock, and slowing the FIGHTER would kill the orbit.
        self._masses({self.ship: 1.0, self.load: 1.0})
        gt.grav_tether_swing(self.load, self.ship, 800)
        gt.grav_tether_tick()
        self.assertFalse(self._has_drag(self.load))
        self.assertFalse(self._has_drag(self.ship))

    def test_drag_is_floored(self):
        # A ship pinned to zero cannot play; the haul should be slow, not impossible.
        self.assertLessEqual(gt._drag_amount(1000.0), 1.0 - gt.DRAG_FLOOR)

    def test_releasing_lifts_the_drag(self):
        self._masses({self.ship: 4.0, self.load: 4.0})
        gt.grav_tether_tow(self.ship, self.load, 500)
        gt.grav_tether_tick()
        self.assertTrue(self._has_drag(self.ship))
        gt.grav_tether_release(self.ship, self.load)
        self.assertFalse(self._has_drag(self.ship))

    # --- grab needs a slowed target ----------------------------------------

    def test_a_ship_under_power_cannot_be_grabbed(self):
        gt.grav_tether_set_grab_speed_limit(0.5)
        to_object(self.load).data_set.set("playerThrottle", 1.0, 0)
        self.assertIsNone(gt.grav_tether_lock(self.ship, self.load))
        self.assertFalse(gt.grav_tether_has(self.ship, self.load))

    def test_a_crippled_ship_can_be_grabbed(self):
        gt.grav_tether_set_grab_speed_limit(0.5)
        to_object(self.load).data_set.set("playerThrottle", 0.1, 0)
        self.assertIsNotNone(gt.grav_tether_lock(self.ship, self.load))

    def test_the_speed_rule_is_off_by_default(self):
        to_object(self.load).data_set.set("playerThrottle", 3.0, 0)
        self.assertIsNotNone(gt.grav_tether_lock(self.ship, self.load))

    # --- power --------------------------------------------------------------

    def test_towing_spends_energy(self):
        self._masses({self.ship: 4.0, self.load: 10.0})
        gt.grav_tether_set_tow_energy_cost(0.02)
        to_object(self.ship).data_set.set("energy", 500.0, 0)
        gt.grav_tether_tow(self.ship, self.load, 500)
        gt.grav_tether_tick()
        self.assertLess(to_object(self.ship).data_set.get("energy", 0), 500.0)

    def test_running_dry_drops_the_load(self):
        # Being slow is a mechanic; being stranded at zero energy is not.
        self._masses({self.ship: 4.0, self.load: 10.0})
        gt.grav_tether_set_tow_energy_cost(0.02)
        to_object(self.ship).data_set.set("energy", 0.05, 0)
        gt.grav_tether_tow(self.ship, self.load, 500)
        gt.grav_tether_tick()
        self.assertFalse(gt.grav_tether_has(self.ship, self.load))


if __name__ == "__main__":
    unittest.main()
