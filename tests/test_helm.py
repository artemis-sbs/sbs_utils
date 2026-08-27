"""Flying a player ship: throttle clamps, steering, docking, and the energy reserve.

The reserve tests are the load-bearing ones. LegendaryMissions' autoplay carries an energy
REFILL cheat, put there so a long unattended run would not stall - and a cheat like that
also hides every real energy bug behind it. It can only be deleted if the bot is provably
unable to strand itself, so these pin the three rules that make that true: warp is refused
without the reserve to reach help, a stop always recovers, and "can I afford to get there"
is asked about a real distance rather than a flat number.

Run:
    python -m unittest tests.test_helm
"""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import sbs_utils.mast_sbs.story_nodes  # import first to break a circular import
from cosmos_dev.mock import sbs as sbs
from tests.reset_helper import reset_mock
from sbs_utils.helpers import Context, FakeEvent, FrameContext
from sbs_utils.procedural.helm import (
    DEFAULT_ENERGY_RESERVE, IMPULSE_MAX, helm_can_turn, helm_distance, helm_dock_request,
    helm_eng_controls, helm_energy, helm_energy_cost, helm_energy_reserve, helm_is_docked,
    helm_set_power, helm_shield_fraction, helm_shields, helm_steer_to_point,
    helm_steer_to_vec, helm_stop, helm_system_damage, helm_system_heat, helm_throttle,
    helm_undock, helm_warp_available)
from sbs_utils.procedural.spawn import npc_spawn, player_spawn
from sbs_utils.spaceobject import SpaceObject


class HelmBase(unittest.TestCase):
    def setUp(self):
        reset_mock(sbs)
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent(0, "test"))
        self.ship = player_spawn(0, 0, 0, "Artemis", "tsn", "tsn_light_cruiser")
        self.ds = self.ship.data_set

    def tearDown(self):
        SpaceObject.clear()
        FrameContext.context = None


class ThrottleTests(HelmBase):
    def test_impulse_is_set_as_asked(self):
        self.assertEqual(helm_throttle(self.ship, 0.5), 0.5)
        self.assertAlmostEqual(self.ds.get("playerThrottle", 0), 0.5)

    def test_warp_is_refused_without_a_warp_drive(self):
        """The engine gates the WARP band on `data_set warp == 1.0`.

        Asking for warp without one does not fail loudly - the ship flies at impulse while
        the caller believes it is going three times faster. Clamping makes that visible in
        the return value.
        """
        self.ds.set("warp", 0.0)
        self.ds.set("warp_energy_cost", 0.0)
        self.assertFalse(helm_warp_available(self.ship))
        self.assertEqual(helm_throttle(self.ship, 3.0), IMPULSE_MAX)

    def test_an_UNSET_warp_field_still_allows_warp(self):
        """THE POLARITY, and it is the whole point of the check.

        The engine returns None for a field nobody set. Treating that as 0 turns "I have
        no information" into "you may never warp" - a capability disabled for the whole
        mission, with no error, on a ship that flies perfectly well. That is far worse
        than the thing the check guards against, which merely wastes a throttle write the
        engine ignores. Unknown must fail OPEN.
        """
        # A stub, not the mock: the mock ALWAYS answers a typed default and never None,
        # which is exactly the engine divergence under test. `--strict-blob` exists for
        # this, but it changes reads globally; a stub says precisely what is being asked.
        from sbs_utils.procedural import helm as H

        class _Unset:
            """An engine-shaped data_set: every field anybody asks for was never set."""
            def get(self, key, index=0):
                return None
            def set(self, *a, **k):
                pass

        real = H._ds
        H._ds = lambda ship: _Unset()
        try:
            self.assertTrue(H.helm_warp_available(self.ship),
                            "unknown must fail OPEN, or warp is disabled for the mission")
            self.assertEqual(H.helm_throttle(self.ship, 3.0), 3.0,
                             "an unset energy field is not an empty tank")
        finally:
            H._ds = real

    def test_a_hull_that_positively_has_no_drive_is_still_refused(self):
        """Both fields present and zero IS evidence, and should still clamp."""
        self.ds.set("warp", 0.0)
        self.ds.set("warp_energy_cost", 0.0)
        self.assertFalse(helm_warp_available(self.ship))
        self.assertEqual(helm_throttle(self.ship, 3.0), IMPULSE_MAX)

    def test_a_warp_cost_alone_is_enough(self):
        """A hull that costs energy to warp plainly has a drive."""
        self.ds.set("warp", 0.0)
        self.ds.set("warp_energy_cost", 5.0)
        self.assertTrue(helm_warp_available(self.ship))

    def test_warp_is_allowed_with_a_drive_and_a_full_tank(self):
        self.ds.set("warp", 1.0)
        self.ds.set("energy", 1000.0)
        self.assertEqual(helm_throttle(self.ship, 3.0), 3.0)

    def test_warp_is_refused_below_the_reserve(self):
        """THE ANTI-STRAND RULE. Warp is the only thing that drains faster than the APU
        refills, so entering it on a low tank is how a ship ends up unable to reach help.
        """
        self.ds.set("warp", 1.0)
        self.ds.set("energy", DEFAULT_ENERGY_RESERVE - 1)
        self.assertEqual(helm_throttle(self.ship, 3.0), IMPULSE_MAX)

    def test_allow_warp_false_holds_impulse_regardless(self):
        self.ds.set("warp", 1.0)
        self.ds.set("energy", 1000.0)
        self.assertEqual(helm_throttle(self.ship, 4.0, allow_warp=False), IMPULSE_MAX)

    def test_reverse_is_minus_one_and_clamps_there(self):
        self.assertEqual(helm_throttle(self.ship, -1.0), -1.0)
        self.assertEqual(helm_throttle(self.ship, -5.0), -1.0)

    def test_throttle_clamps_to_the_bar_maximum(self):
        self.ds.set("warp", 1.0)
        self.ds.set("energy", 1000.0)
        self.assertEqual(helm_throttle(self.ship, 99.0), 5.0)

    def test_stop_cuts_throttle_and_steering(self):
        helm_throttle(self.ship, 1.0)
        helm_steer_to_vec(self.ship, 1, 0, 0)
        helm_stop(self.ship)
        self.assertEqual(self.ds.get("playerThrottle", 0), 0.0)
        self.assertEqual(self.ds.get("steeringToDirFlag", 0), 0)


class EnergyTests(HelmBase):
    def test_a_stopped_ship_always_recovers(self):
        """The floor the whole no-cheat argument rests on.

        The APU tops the tank up whenever energy is below its ceiling, and only throttle
        drains it. So a ship with the throttle at zero cannot get worse - which means
        there is no unrecoverable energy state, and a bot that stalls is one that never
        stopped burning.
        """
        sbs.resume_sim()        # physics_tick returns immediately on a paused sim
        self.ds.set("energy", 10.0)
        helm_stop(self.ship)
        before = helm_energy(self.ship)
        for _ in range(120):
            sbs.physics_tick(1.0 / 30.0)
        self.assertGreater(helm_energy(self.ship), before,
                           "a stopped ship must regain energy, or nothing can be proven")

    def test_warp_drains_faster_than_the_apu_refills(self):
        """The other half of the claim, so it says something.

        If everything recovered regardless of throttle, "stop and you recover" would be
        vacuous. Sustained warp is the one thing that outruns the auxiliary power unit -
        which is exactly why the reserve gate is on warp specifically.
        """
        sbs.resume_sim()
        self.ds.set("warp", 1.0)
        self.ds.set("energy", 900.0)
        self.ds.set("ship_energy_cost", 10.0)
        self.ds.set("warp_energy_cost", 10.0)
        helm_throttle(self.ship, 3.0)
        before = helm_energy(self.ship)
        for _ in range(120):
            sbs.physics_tick(1.0 / 30.0)
        self.assertLess(helm_energy(self.ship), before,
                        "sustained warp must net-drain, or the reserve gate is pointless")

    def test_warp_costs_more_than_impulse(self):
        cheap = helm_energy_cost(self.ship, 1.0, 10)
        dear = helm_energy_cost(self.ship, 3.0, 10)
        self.assertGreater(dear, cheap)

    def test_reserve_without_a_target_is_just_a_floor(self):
        self.ds.set("energy", DEFAULT_ENERGY_RESERVE + 1)
        self.assertTrue(helm_energy_reserve(self.ship))
        self.ds.set("energy", DEFAULT_ENERGY_RESERVE - 1)
        self.assertFalse(helm_energy_reserve(self.ship))

    def test_reserve_asks_about_the_actual_distance(self):
        """This is what a flat "dock below 300" cannot express.

        300 says nothing about whether the station is 2,000 units away or 40,000. The same
        tank should answer yes to the near one and no to the far one.
        """
        self.ds.set("energy", 500.0)
        self.ds.set("ship_energy_cost", 1.0)
        near = npc_spawn(2000, 0, 0, "Near", "tsn", "starbase", "behav_station")
        far = npc_spawn(400000, 0, 0, "Far", "tsn", "starbase", "behav_station")
        self.assertTrue(helm_energy_reserve(self.ship, near, reserve=100),
                        "a nearby station should be affordable")
        self.assertFalse(helm_energy_reserve(self.ship, far, reserve=100),
                         "a station most of a sector away should not be")


class SteeringTests(HelmBase):
    def test_steer_to_vec_normalizes(self):
        self.assertTrue(helm_steer_to_vec(self.ship, 0, 0, 5))
        self.assertAlmostEqual(self.ds.get("steerToDirDZ", 0), 1.0)
        self.assertEqual(self.ds.get("steeringToDirFlag", 0), 1)

    def test_a_zero_vector_is_refused(self):
        self.assertFalse(helm_steer_to_vec(self.ship, 0, 0, 0))

    def test_steer_to_point_points_at_the_target(self):
        other = npc_spawn(0, 0, 1000, "Target", "tsn", "tsn_light_cruiser", "behav_npcship")
        self.assertTrue(helm_steer_to_point(self.ship, other))
        self.assertAlmostEqual(self.ds.get("steerToDirDZ", 0), 1.0)

    def test_distance_is_three_dimensional(self):
        other = npc_spawn(300, 400, 0, "T", "tsn", "tsn_light_cruiser", "behav_npcship")
        self.assertAlmostEqual(helm_distance(self.ship, other), 500.0)


class DockTests(HelmBase):
    def test_dock_request_names_the_base_and_starts_the_walk(self):
        base = npc_spawn(500, 0, 0, "DS1", "tsn", "starbase", "behav_station")
        self.assertTrue(helm_dock_request(self.ship, base))
        self.assertEqual(self.ds.get("dock_base_id", 0), base.id)
        self.assertEqual(self.ds.get("dock_state", 0), "dock_start")
        self.assertEqual(self.ds.get("playerThrottle", 0), 0.0)

    def test_dock_request_does_not_restart_a_finished_dock(self):
        base = npc_spawn(500, 0, 0, "DS1", "tsn", "starbase", "behav_station")
        self.ds.set("dock_state", "docked", 0)
        helm_dock_request(self.ship, base)
        self.assertEqual(self.ds.get("dock_state", 0), "docked")
        self.assertTrue(helm_is_docked(self.ship))

    def test_undock_clears_the_base_too(self):
        """Clearing only the state leaves the ship tractored to a base it thinks it left."""
        base = npc_spawn(500, 0, 0, "DS1", "tsn", "starbase", "behav_station")
        helm_dock_request(self.ship, base)
        helm_undock(self.ship)
        self.assertEqual(self.ds.get("dock_state", 0), "undocked")
        self.assertEqual(self.ds.get("dock_base_id", 0), 0)


class EngineeringTests(HelmBase):
    """The control table is populated by hand here on purpose.

    THE MOCK DOES NOT MODEL `eng_control_label` - it exists only as an empty string in the
    data_set default table, so a headless ship has NO engineering controls at all. That is
    a mock gap worth knowing (autoplay's engineering loop walks the same array and
    therefore does nothing headless), but it is not what these tests are about: they pin
    helm.py's own walk, matching and end-detection, so they supply the table themselves.
    """

    def _controls(self, *labels):
        for i, name in enumerate(labels):
            self.ds.set("eng_control_label", name, i)
            self.ds.set("eng_control_type_index", i, i)

    def test_controls_stop_at_the_first_empty_label(self):
        self._controls("Impulse Drive", "Maneuver", "Beams")
        controls = list(helm_eng_controls(self.ship))
        self.assertEqual([c[1] for c in controls],
                         ["Impulse Drive", "Maneuver", "Beams"])

    def test_an_empty_table_is_not_an_error(self):
        self.assertEqual(list(helm_eng_controls(self.ship)), [])

    def test_set_power_matches_by_substring_and_case(self):
        self._controls("Impulse Drive", "Maneuver")
        self.assertEqual(helm_set_power(self.ship, "impulse", 1.5), 1)
        self.assertAlmostEqual(self.ds.get("eng_control_value", 0), 1.5)

    def test_set_power_sets_every_matching_control(self):
        """A hull can expose more than one control feeding the same system.

        `set_engineering_value` stops at the first match, which silently leaves the
        others alone.
        """
        self._controls("Front Shield", "Rear Shield")
        self.assertEqual(helm_set_power(self.ship, "shield", 2.0), 2)

    def test_system_damage_reads_through_the_type_index(self):
        self._controls("Maneuver")
        self.ds.set("system_max_damage", 100.0, 0)
        self.ds.set("system_damage", 90.0, 0)
        self.assertAlmostEqual(helm_system_damage(self.ship, "maneuver"), 0.9)

    def test_can_turn_is_false_with_a_wrecked_maneuver_system(self):
        """Both halves matter: a wrecked maneuver system stops the ship turning before
        the damage coefficient bottoms out."""
        self._controls("Maneuver")
        self.ds.set("turn_damage_coeff", 1.0, 0)
        self.ds.set("system_max_damage", 100.0, 0)
        self.ds.set("system_damage", 90.0, 0)
        self.assertFalse(helm_can_turn(self.ship))

    def test_can_turn_is_true_on_a_healthy_ship(self):
        self.assertTrue(helm_can_turn(self.ship))

    def test_can_turn_is_false_with_the_coefficient_bottomed_out(self):
        self.ds.set("turn_damage_coeff", 0.1, 0)
        self.assertFalse(helm_can_turn(self.ship))

    def test_system_damage_and_heat_default_to_zero(self):
        self.assertEqual(helm_system_damage(self.ship, "maneuver"), 0.0)
        self.assertEqual(helm_system_heat(self.ship, "maneuver"), 0.0)

    def test_a_none_field_does_not_raise(self):
        """The engine answers None for a field nobody set; the mock answers a typed
        default. Code that reads one and compares it is exactly how two crashes shipped."""
        self.ds.set("turn_damage_coeff", None, 0)
        helm_can_turn(self.ship)        # must not raise


class ShieldTests(HelmBase):
    def test_shields_raise_and_lower(self):
        helm_shields(self.ship, True)
        self.assertEqual(self.ds.get("shields_raised_flag", 0), 1)
        helm_shields(self.ship, False)
        self.assertEqual(self.ds.get("shields_raised_flag", 0), 0)

    def test_shield_fraction_is_zero_without_shields(self):
        self.ds.set("shield_max_val", 0.0, 0)
        self.assertEqual(helm_shield_fraction(self.ship), 0.0)


if __name__ == "__main__":
    unittest.main()
