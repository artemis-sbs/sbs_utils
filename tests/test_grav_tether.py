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
from sbs_utils.procedural.terrain import terrain_spawn_black_hole
from sbs_utils.vec import Vec3


class TestGravTether(unittest.TestCase):
    def setUp(self):
        reset_mock(sbs)
        gt.grav_tether_clear_all()
        gt.grav_tether_set_overspeed_default(gt.OVERSPEED_CAP)
        gt.grav_tether_set_attach_policy(None)
        # A provider leaked from another class would change the stiffness assertions here
        # and the failure would look like this file's bug rather than that one's.
        gt.grav_tether_set_mass_fn(None)
        gt.grav_tether_set_pull_bonus_fn(None)
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

    def test_between_sees_a_tether_from_either_end(self):
        # `has` is DIRECTIONAL and a swing is registered (anchor, ship), so a menu asking
        # has(me, that) is blind to the swing it opened itself - it re-offers the grab and
        # never offers Release, and the crew cannot let go.
        gt.grav_tether_swing(self.load, self.ship, 800)
        self.assertFalse(gt.grav_tether_has(self.ship, self.load))
        self.assertTrue(gt.grav_tether_between(self.ship, self.load))
        self.assertTrue(gt.grav_tether_between(self.load, self.ship))

    def test_release_between_lets_go_whichever_end_opened_it(self):
        gt.grav_tether_swing(self.load, self.ship, 800)
        gt.grav_tether_release_between(self.ship, self.load)
        self.assertFalse(gt.grav_tether_between(self.ship, self.load))
        gt.grav_tether_tow(self.ship, self.load, 500)
        gt.grav_tether_release_between(self.ship, self.load)
        self.assertFalse(gt.grav_tether_between(self.ship, self.load))

    def test_between_is_false_for_strangers(self):
        self.assertFalse(gt.grav_tether_between(self.ship, self.load))
        self.assertFalse(gt.grav_tether_between(self.ship, 0))

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

    def test_lock_up_close_is_rigid(self):
        # The case the mode was written for (hangar recovery): already in reach, so the
        # rigid grab is immediate and unchanged.
        to_object(self.load).pos = sbs.vec3(50, 0, 0)
        con = gt.grav_tether_lock(self.ship, self.load)
        self.assertEqual(con.offset, 0.0)
        self.assertEqual(gt._TETHERS[(self.ship, self.load)]["pull"], 0.0)
        self.assertFalse(gt._TETHERS[(self.ship, self.load)].get("winch"))

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
        # attach, not lock: a lock at 2000u now WINCHES (rigid across a gap teleported the
        # load, see TestGravLockAtRange). The raw rigid attach is what this is measuring.
        gt.grav_tether_attach(self.ship, self.load)   # offset 0 -> rigid snap
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


class TestHeavyTow(unittest.TestCase):
    """Dragging a starbase is allowed, and it has to cost something.

    A TOW deliberately does not mass-reverse (a lock does) - a crew that picked "Tow"
    asked to be the one pulling. But the load's own motion was not mass-aware at all:
    _tick_rope set a flat stiffness, so a 200-mass station reeled to the rope exactly as
    fast as a 1-mass fighter. The tug paid in drag and power; the station was free.
    """

    def setUp(self):
        reset_mock(sbs)
        gt.grav_tether_clear_all()
        gt.grav_tether_set_attach_policy(None)
        gt.grav_tether_set_grab_speed_limit(None)
        gt.grav_tether_set_range_limit(None)
        gt.grav_tether_set_tow_energy_cost(0.0)
        side_ensure("tsn", "TSN")
        self.ship = to_id(player_spawn(0, 0, 0, "Tug", "tsn", "tsn_light_cruiser"))
        self.mate = to_id(player_spawn(0, 0, 100, "Mate", "tsn", "tsn_light_cruiser"))
        self.base = to_id(npc_spawn(3000, 0, 0, "Base", "tsn", "starbase_command",
                                    "behav_station"))
        self.rock = to_id(npc_spawn(3000, 0, 0, "Rock", "tsn", "tsn_fighter",
                                    "behav_npcship"))
        self._masses({self.ship: 3.0, self.mate: 3.0, self.base: 200.0, self.rock: 1.0})

    def tearDown(self):
        gt.grav_tether_clear_all()
        gt.grav_tether_set_mass_fn(None)
        gt.grav_tether_set_pull_bonus_fn(None)
        gt.grav_tether_set_tow_energy_cost(0.0)
        gt._release_drag(self.ship)
        gt._release_drag(self.mate)

    def _masses(self, table):
        gt.grav_tether_set_mass_fn(lambda oid: table.get(oid, 1.0))

    def _lag(self, src, tgt):
        """The stiffness the rope tick actually put on the live connection."""
        gt.grav_tether_tick()
        return gt.grav_tether_get(src, tgt).offset

    # --- the beam has to feel the weight ------------------------------------

    def test_a_light_load_tows_exactly_as_it_always_did(self):
        # The no-regression guard. Every existing tow, and every mission that installs no
        # mass table at all, must come out at the nominal stiffness.
        gt.grav_tether_tow(self.ship, self.rock, 500)
        self.assertEqual(self._lag(self.ship, self.rock), gt.DEFAULT_TOW_STIFFNESS)

    def test_no_mass_provider_means_no_extra_lag(self):
        gt.grav_tether_set_mass_fn(None)
        gt.grav_tether_tow(self.ship, self.base, 500)
        self.assertEqual(self._lag(self.ship, self.base), gt.DEFAULT_TOW_STIFFNESS)

    def test_a_starbase_wallows(self):
        """con.offset is a SPEED, engine-measured at offset x 30.2 u/s - so a heavy load
        DIVIDES it down. The first version of this multiplied, which reeled a starbase in
        four times faster than a fighter; only a mock calibrated to the engine caught it."""
        gt.grav_tether_tow(self.ship, self.base, 500)
        self.assertLess(self._lag(self.ship, self.base), gt.DEFAULT_TOW_STIFFNESS / 5)

    def test_a_second_tug_makes_the_load_move_better(self):
        """More pull mass means a FASTER beam, because offset is a speed. A clamped or
        floored-out curve would make these two equal and cooperating would buy nothing."""
        gt.grav_tether_tow(self.ship, self.base, 500)
        solo = self._lag(self.ship, self.base)
        gt.grav_tether_tow(self.mate, self.base, 500)
        self.assertGreater(self._lag(self.ship, self.base), solo)

    def test_the_lag_really_does_slow_the_load_down(self):
        """Not just a smaller number - measurably less distance closed, against a mock
        whose tractor model is calibrated to a controlled engine sweep."""
        def close(target):
            gt.grav_tether_clear_all()
            to_object(target).pos = sbs.vec3(3000, 0, 0)
            gt.grav_tether_tow(self.ship, target, 100)
            gt.grav_tether_tick()
            sbs.sim._paused = False
            for _ in range(300):                       # 10s at 1/30
                sbs.sim._paused = False
                sbs._physics_tractors(sbs.sim, 1 / 30.0)
            return 3000 - to_object(target).pos.x
        self.assertLess(close(self.base), close(self.rock) / 2)

    # --- a tow never flips, however heavy -----------------------------------

    def test_towing_a_station_still_pulls_the_station(self):
        gt.grav_tether_tow(self.ship, self.base, 500)
        gt.grav_tether_tick()
        self.assertIsNotNone(sbs.sim.GetTractorConnection(self.ship, self.base))
        self.assertIsNone(sbs.sim.GetTractorConnection(self.base, self.ship))
        self.assertFalse(gt._TETHERS[(self.ship, self.base)].get("reversed"))

    # --- the power bill is shared -------------------------------------------

    def _burn(self, pullers):
        gt.grav_tether_clear_all()
        gt.grav_tether_set_tow_energy_cost(0.02)
        for p in pullers:
            to_object(p).data_set.set("energy", 1000.0, 0)
            gt.grav_tether_tow(p, self.base, 500)
        gt.grav_tether_tick()
        return 1000.0 - to_object(pullers[0]).data_set.get("energy", 0)

    def test_one_tug_pays_what_it_always_paid(self):
        self.assertAlmostEqual(self._burn([self.ship]), 0.02 * 200.0, places=4)

    def test_two_tugs_each_pay_half(self):
        """Unshared, four hulls each drain at the solo rate and all cut out together -
        the fleet spends four times the power for not one extra second of haul."""
        self.assertAlmostEqual(self._burn([self.ship, self.mate]), 0.02 * 200.0 / 2,
                               places=4)

    # --- drag is a share of the load, not all of it -------------------------

    def test_a_second_tug_lightens_the_first_ones_drag(self):
        self._masses({self.ship: 3.0, self.mate: 3.0, self.base: 8.0, self.rock: 1.0})
        gt.grav_tether_tow(self.ship, self.base, 500)
        gt.grav_tether_tick()
        alone = gt._TETHERS[(self.ship, self.base)]["drag"]
        gt.grav_tether_tow(self.mate, self.base, 500)
        gt.grav_tether_tick()
        self.assertLess(gt._TETHERS[(self.ship, self.base)]["drag"], alone)

    def test_a_tug_letting_go_puts_the_weight_back_on_the_survivor(self):
        self._masses({self.ship: 3.0, self.mate: 3.0, self.base: 8.0, self.rock: 1.0})
        gt.grav_tether_tow(self.ship, self.base, 500)
        gt.grav_tether_tow(self.mate, self.base, 500)
        gt.grav_tether_tick()
        shared = gt._TETHERS[(self.ship, self.base)]["drag"]
        gt.grav_tether_release(self.mate, self.base)
        gt.grav_tether_tick()
        self.assertGreater(gt._TETHERS[(self.ship, self.base)]["drag"], shared)

    # --- and it says so ------------------------------------------------------

    def test_strain_is_announced_once_per_band_not_once_per_tick(self):
        said = []
        real, gt.signal_emit = gt.signal_emit, lambda n, d=None: said.append((n, d))
        try:
            gt.grav_tether_tow(self.ship, self.base, 500)
            gt.grav_tether_tick()
            gt.grav_tether_tick()
            gt.grav_tether_tick()
            strains = [d for n, d in said if n == "grav_tether_strain"]
            self.assertEqual(len(strains), 1, "a tick-rate signal is a flood, not feedback")
            self.assertEqual(strains[0]["STRAIN"], "overloaded")
            self.assertEqual(strains[0]["PULLERS"], 1)
        finally:
            gt.signal_emit = real

    def test_an_easy_tow_says_nothing(self):
        said = []
        real, gt.signal_emit = gt.signal_emit, lambda n, d=None: said.append(n)
        try:
            gt.grav_tether_tow(self.ship, self.rock, 500)
            gt.grav_tether_tick()
            self.assertNotIn("grav_tether_strain", said)
        finally:
            gt.signal_emit = real

    def test_the_readout_can_see_the_strain_without_internals(self):
        gt.grav_tether_tow(self.ship, self.base, 500)
        st = gt.grav_tether_status(self.ship)
        self.assertEqual(st["strain"], "overloaded")
        self.assertEqual(st["pullers"], 1)
        gt.grav_tether_tow(self.mate, self.base, 500)
        self.assertEqual(gt.grav_tether_status(self.ship)["pullers"], 2)

    def test_the_pull_has_a_floor_and_the_floor_is_not_zero(self):
        """A mass table is a mission's to write and nothing stops it holding 100000.
        Without a floor that ratio divides the dial to nothing - and offset 0 is the RIGID
        case, which puts the load on the source point in a single tick. The gentlest
        possible tow would become a teleport."""
        self._masses({self.ship: 1.0, self.base: 100000.0})
        gt.grav_tether_tow(self.ship, self.base, 500)
        lag = self._lag(self.ship, self.base)
        self.assertEqual(lag, gt.DEFAULT_TOW_STIFFNESS * gt.TOW_LAG_MIN_SCALE)
        self.assertGreater(lag, 0.0, "offset 0 is a snap, not a slow pull")

    def test_lock_and_swing_stiffness_are_untouched_by_mass(self):
        """The Lock/Tow split, as an assertion. A lock on something heavy is REVERSED -
        the station is pulling YOU, and that should be strong, not sluggish - and a
        swing's anchor is a rock, where scaling would kill the orbit the mode exists for.
        """
        gt.grav_tether_swing(self.base, self.ship, 800)
        gt.grav_tether_tick()
        self.assertEqual(gt.grav_tether_get(self.base, self.ship).offset, 1.0)
        gt.grav_tether_clear_all()
        gt.grav_tether_lock(self.ship, self.base)
        self.assertEqual(gt._TETHERS[(self.ship, self.base)]["stiffness"],
                         gt.LOCK_WINCH_STIFFNESS)

    def test_pull_mass_ignores_beams_that_are_not_hauling(self):
        """A swing's source is an anchor and a reversed tether's source is the LOAD.
        Counting either inflates the crew and makes the haul look lighter than it is."""
        gt.grav_tether_swing(self.base, self.ship, 800)          # anchor is not hauling
        self.assertEqual(gt.grav_tether_pullers_of(self.ship), [])
        gt.grav_tether_clear_all()
        gt.grav_tether_lock(self.ship, self.base)                # reverses: ship is load
        self.assertTrue(gt._TETHERS[(self.ship, self.base)]["reversed"])
        self.assertEqual(gt.grav_tether_pullers_of(self.base), [])

    def test_a_tug_rig_counts_as_extra_hulls(self):
        """The rig is worth exactly what bringing that many more ships is worth, so the
        readout can never say two different things about the same fact."""
        gt.grav_tether_tow(self.ship, self.base, 500)
        solo = self._lag(self.ship, self.base)
        gt.grav_tether_set_pull_bonus_fn(lambda oid: 4.0)
        self.assertGreater(self._lag(self.ship, self.base), solo)
        self.assertEqual(gt.grav_tether_pull_mass(self.base), 12.0)
        gt.grav_tether_set_pull_bonus_fn(None)

    def test_a_rig_does_not_make_you_harder_to_grab_or_worth_more_dead(self):
        """Why the bonus is its own hook and not just added to the mass table: mass also
        decides whether a Grav Lock reverses onto you and, in a mission that prices
        salvage by mass, what your own wreck pays."""
        gt.grav_tether_set_pull_bonus_fn(lambda oid: 4.0)
        self.assertEqual(gt.grav_tether_mass(self.ship), 3.0)
        gt.grav_tether_set_pull_bonus_fn(None)

    def test_pull_mass_sums_and_a_free_load_is_neutral(self):
        gt.grav_tether_tow(self.ship, self.base, 500)
        self.assertEqual(gt.grav_tether_pull_mass(self.base), 3.0)
        gt.grav_tether_tow(self.mate, self.base, 500)
        self.assertEqual(gt.grav_tether_pull_mass(self.base), 6.0)
        self.assertEqual(gt.grav_tether_pull_mass(self.rock), gt.DEFAULT_MASS)


class TestGravTetherAnchors(unittest.TestCase):
    """An anchor is something you hang a rope FROM, never something you pull.

    A rigid Grav Lock on a black hole was reachable from the shipped Weapons hold-click,
    and it took whole games down: the beam makes the hole the LOAD, _enforce_impulse then
    caps the puller to impulse so it cannot warp away, and LM's lethal-proximity watch
    explodes anything within 500u of a hole every tick.
    """

    def setUp(self):
        reset_mock(sbs)
        gt.grav_tether_clear_all()
        gt.grav_tether_set_attach_policy(None)
        gt.grav_tether_set_mass_fn(None)
        gt.grav_tether_set_grab_speed_limit(None)
        gt.grav_tether_set_anchor_roles(gt.ANCHOR_ROLES)
        self.ship = to_id(player_spawn(0, 0, 0, "Tug", "tsn", "tsn_light_cruiser"))
        self.hole = to_id(terrain_spawn_black_hole(3000, 0, 0, gravity_radius=5000))
        self.said = []
        self._real_emit = gt.signal_emit
        gt.signal_emit = lambda name, data=None: self.said.append(name)

    def tearDown(self):
        gt.signal_emit = self._real_emit
        gt.grav_tether_clear_all()
        gt.grav_tether_set_anchor_roles(gt.ANCHOR_ROLES)

    def test_a_black_hole_is_an_anchor(self):
        self.assertTrue(gt.grav_tether_is_anchor(self.hole))
        self.assertFalse(gt.grav_tether_is_anchor(self.ship))

    def test_a_black_hole_cannot_be_grav_locked(self):
        self.assertIsNone(gt.grav_tether_lock(self.ship, self.hole))
        self.assertFalse(gt.grav_tether_has(self.ship, self.hole))
        self.assertIsNone(gt.grav_tether_get(self.ship, self.hole))

    def test_a_black_hole_cannot_be_towed_or_reeled(self):
        self.assertIsNone(gt.grav_tether_tow(self.ship, self.hole, 500))
        self.assertIsNone(gt.grav_tether_reel(self.ship, self.hole))
        self.assertFalse(gt.grav_tether_involves(self.hole))

    def test_the_refusal_says_why(self):
        # A button that silently does nothing reads as broken; the mission needs to be
        # able to tell the crew what happened.
        gt.grav_tether_lock(self.ship, self.hole)
        self.assertIn("grav_tether_immovable", self.said)

    def test_nothing_ever_pulls_the_hole(self):
        # The failure was physical: with a connection live the mock (and, on the evidence,
        # the engine) moves the target. No connection, no move.
        before = (to_object(self.hole).pos.x, to_object(self.hole).pos.z)
        gt.grav_tether_lock(self.ship, self.hole)
        for _ in range(5):
            gt.grav_tether_tick()
        after = (to_object(self.hole).pos.x, to_object(self.hole).pos.z)
        self.assertEqual(before, after)

    def test_a_hole_can_still_ANCHOR_a_swing(self):
        # The whole point of the source/target distinction: the slingshot must survive.
        con = gt.grav_tether_swing(self.hole, self.ship, 8000)
        self.assertIsNotNone(con)
        self.assertTrue(gt.grav_tether_has(self.hole, self.ship))

    def test_a_mission_can_clear_the_rule(self):
        gt.grav_tether_set_anchor_roles("")
        self.assertIsNotNone(gt.grav_tether_lock(self.ship, self.hole))


class TestGravTetherReach(unittest.TestCase):
    """How far a beam reaches to open, and how far it stretches before it lets go.

    The library shipped with neither: a gunner could tether something 30,000u off the
    tactical picture. The NUMBER belongs to a mission, so all of this is inert until one
    installs a limit - which is what the last test here pins.
    """

    def setUp(self):
        reset_mock(sbs)
        gt.grav_tether_clear_all()
        gt.grav_tether_set_attach_policy(None)
        gt.grav_tether_set_mass_fn(None)
        gt.grav_tether_set_grab_speed_limit(None)
        gt.grav_tether_set_range_limit(None)
        self.ship = to_id(player_spawn(0, 0, 0, "Tug", "tsn", "tsn_light_cruiser"))
        self.near = to_id(npc_spawn(1000, 0, 0, "Near", "tsn", "tsn_light_cruiser",
                                    "behav_npcship"))
        self.far = to_id(npc_spawn(30000, 0, 0, "Far", "tsn", "tsn_light_cruiser",
                                   "behav_npcship"))
        self.said = []
        self._real_emit = gt.signal_emit
        gt.signal_emit = lambda name, data=None: self.said.append(name)

    def tearDown(self):
        gt.signal_emit = self._real_emit
        gt.grav_tether_clear_all()
        gt.grav_tether_set_range_limit(None)

    def _move(self, oid, x):
        to_object(oid).pos = Vec3(x, 0, 0)

    def test_in_reach_opens_and_out_of_reach_does_not(self):
        gt.grav_tether_set_range_limit(8000)
        self.assertIsNotNone(gt.grav_tether_tow(self.ship, self.near, 500))
        self.assertIsNone(gt.grav_tether_tow(self.ship, self.far, 500))

    def test_the_refusal_says_why(self):
        gt.grav_tether_set_range_limit(8000)
        gt.grav_tether_lock(self.ship, self.far)
        self.assertIn("grav_tether_out_of_reach", self.said)

    def test_no_limit_is_the_old_unlimited_behavior(self):
        # The rule is opt-in. A mission that never installs a number gets exactly what
        # the library shipped with.
        self.assertIsNone(gt.grav_tether_range_limit())
        self.assertIsNotNone(gt.grav_tether_tow(self.ship, self.far, 500))

    def test_a_tether_dragged_too_far_snaps(self):
        gt.grav_tether_set_range_limit(8000)
        gt.grav_tether_tow(self.ship, self.near, 500)
        self._move(self.near, 20000)                 # hauled well past breaking
        gt.grav_tether_tick()
        self.assertFalse(gt.grav_tether_has(self.ship, self.near))
        self.assertIn("grav_tether_snapped", self.said)

    def test_a_tow_reeling_a_load_IN_does_not_snap_itself(self):
        # The trap the hold-distance rule exists for. A rope-toggle tow is SUPPOSED to sit
        # beyond its rope - that is the state in which the pull engages - so measuring the
        # stretch against rope_len alone would snap a 500u tow on its first tick.
        gt.grav_tether_set_range_limit(8000)
        gt.grav_tether_tow(self.ship, self.near, 500)
        self._move(self.near, 2000)
        gt.grav_tether_tick()
        self.assertTrue(gt.grav_tether_has(self.ship, self.near))

    def test_a_rope_longer_than_the_reach_is_measured_against_itself(self):
        # A wide slingshot arc is 8000u of rope under an 8000u reach. Measured against the
        # reach alone it would be permanently on the edge of snapping.
        gt.grav_tether_set_range_limit(8000)
        self._move(self.near, 8000)
        gt.grav_tether_swing(self.ship, self.near, 8000)
        gt.grav_tether_tick()
        self.assertTrue(gt.grav_tether_has(self.ship, self.near))


class TestGravLockAtRange(unittest.TestCase):
    """A Grav Lock across a gap must CLOSE it, not skip it.

    Reported from a real bridge: grav-lock a starbase from ~7000u and you are instantly
    beside it. Two shipped decisions meet here. Rigid means stiffness 0, and stiffness 0
    has no rate limit - the mock's own tractor physics reads `if con._offset <= 0.0: frac
    = 1.0  # rigid lock: snap to the point`, which is what the engine does too. And the
    mass rule flips a grab on something far heavier, so on a starbase the connection is
    built (station, player): the end that gets snapped across the gap is the PLAYER.

    Neither was visible until a range limit made a lock at that distance legal at all.
    """

    def setUp(self):
        reset_mock(sbs)
        gt.grav_tether_clear_all()
        gt.grav_tether_set_attach_policy(None)
        gt.grav_tether_set_grab_speed_limit(None)
        gt.grav_tether_set_range_limit(8000)
        gt.grav_tether_set_lock_grab_distance(None)
        self.ship = to_id(player_spawn(0, 0, 0, "Tug", "tsn", "tsn_light_cruiser"))
        self.station = to_id(npc_spawn(7000, 0, 0, "Base", "tsn", "starbase_command",
                                       "behav_station"))
        gt.grav_tether_set_mass_fn(lambda oid: 200.0 if oid == self.station else 5.0)

    def tearDown(self):
        gt.grav_tether_clear_all()
        gt.grav_tether_set_mass_fn(None)
        gt.grav_tether_set_range_limit(None)
        gt.grav_tether_set_lock_grab_distance(None)

    def _sep(self):
        import math
        a, b = to_object(self.ship).pos, to_object(self.station).pos
        return math.dist((a.x, a.y, a.z), (b.x, b.y, b.z))

    def test_locking_a_station_at_range_does_not_teleport_you(self):
        """THE BUG. Without the winch this closes 7000u in a single 0.1s physics tick."""
        gt.grav_tether_lock(self.ship, self.station)
        sbs.sim._paused = False
        sbs.physics_tick(0.1)
        self.assertGreater(self._sep(), 5000,
                           "a rigid lock snapped the player onto the station")

    def test_the_beam_is_not_rigid_while_it_is_still_closing(self):
        con = gt.grav_tether_lock(self.ship, self.station)
        self.assertEqual(con.offset, gt.LOCK_WINCH_STIFFNESS)
        self.assertTrue(gt._TETHERS[(self.ship, self.station)]["winch"])

    def test_it_goes_rigid_once_the_gap_is_closed(self):
        gt.grav_tether_lock(self.ship, self.station)
        to_object(self.ship).pos = sbs.vec3(6950, 0, 0)       # winched in
        gt.grav_tether_tick()
        st = gt._TETHERS[(self.ship, self.station)]
        self.assertFalse(st["winch"])
        self.assertEqual(st["stiffness"], 0.0)
        self.assertEqual(gt.grav_tether_get(self.station, self.ship).offset, 0.0)

    def test_arriving_says_so(self):
        said = []
        real, gt.signal_emit = gt.signal_emit, lambda n, d=None: said.append(n)
        try:
            gt.grav_tether_lock(self.ship, self.station)
            gt.grav_tether_tick()
            self.assertNotIn("grav_tether_locked", said, "not there yet")
            to_object(self.ship).pos = sbs.vec3(6950, 0, 0)
            gt.grav_tether_tick()
            self.assertIn("grav_tether_locked", said)
        finally:
            gt.signal_emit = real

    def test_a_winching_lock_still_releases_from_the_callers_terms(self):
        gt.grav_tether_lock(self.ship, self.station)
        gt.grav_tether_release_between(self.ship, self.station)
        self.assertFalse(gt.grav_tether_between(self.ship, self.station))
        self.assertIsNone(sbs.sim.GetTractorConnection(self.station, self.ship))

    def test_being_the_load_does_not_also_cost_you_your_drive(self):
        """The other half of the report: "engines don't work" while tethered.

        Drag is what HAULING costs. On a reversed tether the caller is the load - the
        engine is already moving their hull - and a starbase ratio pins the amount at the
        0.75 ceiling, so they were capped to impulse AND cut to the drag floor at once.
        """
        gt.grav_tether_lock(self.ship, self.station)
        gt.grav_tether_tick()
        from sbs_utils.procedural.inventory import get_inventory_value
        mods = get_inventory_value(self.ship, "impulse_upgrade_coeff_modifiers", [])
        self.assertEqual([m for m in mods if m.source == gt._DRAG_KEY], [])


class TestGravTetherTickIsUnkillable(unittest.TestCase):
    """A raise inside the tether tick does not stop at this module.

    TickTask._update and TickDispatcher.dispatch_tick are both bare, so it aborts every
    OTHER scheduled task that tick and lands in handlerhooks' catch-all, which pauses the
    sim and pushes the ErrorPage - and TickTask.start is only refreshed after the callback
    RETURNS, so Resume Mission re-raises it immediately. The loop must swallow and drop.
    """

    def setUp(self):
        reset_mock(sbs)
        gt.grav_tether_clear_all()
        gt.grav_tether_set_attach_policy(None)
        gt.grav_tether_set_anchor_roles(gt.ANCHOR_ROLES)
        self.ship = to_id(player_spawn(0, 0, 0, "Tug", "tsn", "tsn_light_cruiser"))
        self.load = to_id(npc_spawn(2000, 0, 0, "Load", "tsn", "tsn_light_cruiser", "behav_npcship"))

    def tearDown(self):
        gt.grav_tether_clear_all()

    def test_an_engine_that_refuses_the_beam_drops_the_tether(self):
        gt.grav_tether_reel(self.ship, self.load, rate=10)
        self.assertTrue(gt.grav_tether_has(self.ship, self.load))
        real = sbs.sim.AddTractorConnection
        try:
            sbs.simulation.AddTractorConnection = lambda *a, **k: None
            gt.grav_tether_tick()                     # must not raise
        finally:
            sbs.simulation.AddTractorConnection = real
        self.assertFalse(gt.grav_tether_has(self.ship, self.load))

    def test_a_raising_tether_is_dropped_not_propagated(self):
        gt.grav_tether_tow(self.ship, self.load, 500)
        real = gt._tick_rope
        try:
            def boom(*a, **k):
                raise RuntimeError("engine said no")
            gt._tick_rope = boom
            gt.grav_tether_tick()                     # must not raise
        finally:
            gt._tick_rope = real
        self.assertFalse(gt.grav_tether_has(self.ship, self.load))

    def test_one_bad_tether_does_not_cost_the_others_their_tick(self):
        other = to_id(npc_spawn(9000, 0, 0, "Two", "tsn", "tsn_light_cruiser", "behav_npcship"))
        gt.grav_tether_tow(self.ship, self.load, 500)
        gt.grav_tether_tow(self.ship, other, 500)
        real = gt._tick_rope
        try:
            def boom(src, tgt, st):
                if tgt == self.load:
                    raise RuntimeError("engine said no")
                return real(src, tgt, st)
            gt._tick_rope = boom
            gt.grav_tether_tick()
        finally:
            gt._tick_rope = real
        self.assertFalse(gt.grav_tether_has(self.ship, self.load))
        self.assertTrue(gt.grav_tether_has(self.ship, other))


if __name__ == "__main__":
    unittest.main()
