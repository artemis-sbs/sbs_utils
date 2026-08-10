"""orbit primitive - capture geometry, the weld, and cleanup.

The PHYSICS is engine-native: the engine holds a welded object in its host's body frame
every frame (measured in LM_TestRange/maps/test_tractor_mount.mast, quoted in mount.py).
Asking the mock "does the weld hold?" would be asking our own model, so these do not.

What they cover is the Python we own: that capture builds exactly one carrier with the
right circle and the right engine call, that the orbit frame reproduces the plane and the
direction the ship arrived on, that the carrier is given performance its circle can
actually be flown at, and that every way an orbit can end cleans up after itself.

We weld at offset (0,0,0), where the mock's world-space tractor model and the engine's
body-frame behavior coincide - so the connection assertions here are not testing a
divergence between them.
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import math
import unittest

from cosmos_dev.mock import sbs
from tests.reset_helper import reset_mock
from sbs_utils.procedural.query import object_exists, to_id, to_object
from sbs_utils.procedural.roles import role
from sbs_utils.procedural.spawn import npc_spawn, player_spawn, terrain_spawn
from sbs_utils.procedural import orbit as ob


GIANT_RADIUS = 4000.0


class OrbitTestBase(unittest.TestCase):
    def setUp(self):
        reset_mock(sbs)
        self.giant = to_object(terrain_spawn(0, 0, 0, "Giant", "#,gasgiant",
                                             "planet", "behav_planet"))
        # A gas giant's exclusion radius is planet_radius * 2 - the convention every
        # mission's planet prefab follows, and the reason the orbit floor matters.
        self.giant.engine_object.exclusion_radius = GIANT_RADIUS * 2.0
        self.giant_id = self.giant.id
        self.ship = to_object(player_spawn(12000, 0, 0, "Artemis", "tsn",
                                           "tsn_battleship"))
        self.ship_id = self.ship.id
        self.ship.data_set.set("dock_state", "docked", 0)

    def tearDown(self):
        ob.orbit_release_all()

    def _connected(self, a, b):
        try:
            return sbs.sim.GetTractorConnection(a, b) is not None
        except Exception:
            return False

    def _carrier(self):
        return ob.orbit_carrier_of(self.ship_id)

    def _radius_now(self, carrier_id):
        c = to_object(carrier_id)
        return math.sqrt((c.pos.x - self.giant.pos.x) ** 2
                         + (c.pos.y - self.giant.pos.y) ** 2
                         + (c.pos.z - self.giant.pos.z) ** 2)


class TestCapture(OrbitTestBase):
    def test_capture_creates_one_carrier_and_one_weld(self):
        carrier_id = ob.orbit_capture(self.ship_id, self.giant_id)
        self.assertIsNotNone(carrier_id)
        self.assertTrue(self._connected(carrier_id, self.ship_id))
        self.assertEqual(len(role(ob.ORBIT_CARRIER_ROLE)), 1)
        self.assertEqual(ob.orbit_count(), 1)

    def test_capture_records_both_directions(self):
        carrier_id = ob.orbit_capture(self.ship_id, self.giant_id)
        self.assertTrue(ob.orbit_is(self.ship_id))
        self.assertEqual(ob.orbit_carrier_of(self.ship_id), carrier_id)
        self.assertEqual(ob.orbit_center_of(self.ship_id), self.giant_id)
        self.assertIn(self.ship_id, ob.orbit_riders())

    def test_capture_is_idempotent(self):
        first = ob.orbit_capture(self.ship_id, self.giant_id)
        second = ob.orbit_capture(self.ship_id, self.giant_id)
        self.assertEqual(first, second)
        self.assertEqual(ob.orbit_count(), 1)
        self.assertEqual(len(role(ob.ORBIT_CARRIER_ROLE)), 1)

    def test_carrier_starts_on_the_circle_at_the_ships_position(self):
        carrier_id = ob.orbit_capture(self.ship_id, self.giant_id)
        self.assertAlmostEqual(self._radius_now(carrier_id), 12000.0, delta=1.0)

    def test_radius_defaults_to_the_current_distance(self):
        ob.orbit_capture(self.ship_id, self.giant_id)
        self.assertAlmostEqual(ob.orbit_radius_of(self.ship_id), 12000.0, delta=1.0)

    def test_radius_is_floored_clear_of_the_body(self):
        # Asking to orbit deep inside a gas giant must not be honored.
        ob.orbit_capture(self.ship_id, self.giant_id, radius=100)
        floor = GIANT_RADIUS * 2.0 * ob.ORBIT_RADIUS_CLEARANCE
        self.assertAlmostEqual(ob.orbit_radius_of(self.ship_id), floor, delta=1.0)

    def test_capture_needs_two_real_objects(self):
        self.assertIsNone(ob.orbit_capture(self.ship_id, None))
        self.assertIsNone(ob.orbit_capture(None, self.giant_id))
        self.assertIsNone(ob.orbit_capture(self.ship_id, self.ship_id))
        self.assertEqual(ob.orbit_count(), 0)

    def test_capture_drops_the_engines_docking_tractor(self):
        # The engine tractors the docking pair itself and expects the script to delete it;
        # leaving it live is two tractors arguing over one hull.
        sbs.sim.AddTractorConnection(self.giant_id, self.ship_id, sbs.vec3(0, 0, 0), 0)
        self.assertTrue(self._connected(self.giant_id, self.ship_id))
        ob.orbit_capture(self.ship_id, self.giant_id)
        self.assertFalse(self._connected(self.giant_id, self.ship_id))


class TestOrbitFrame(OrbitTestBase):
    def _frame(self, carrier_id):
        from sbs_utils.procedural.inventory import get_inventory_value
        return (get_inventory_value(carrier_id, ob.ORBIT_KEY_RADIAL, None),
                get_inventory_value(carrier_id, ob.ORBIT_KEY_TANGENT, None))

    def test_radial_points_from_the_center_out_to_the_ship(self):
        carrier_id = ob.orbit_capture(self.ship_id, self.giant_id)
        r, _ = self._frame(carrier_id)
        self.assertAlmostEqual(r[0], 1.0, places=5)
        self.assertAlmostEqual(r[1], 0.0, places=5)
        self.assertAlmostEqual(r[2], 0.0, places=5)

    def test_frame_is_orthonormal(self):
        carrier_id = ob.orbit_capture(self.ship_id, self.giant_id)
        r, t = self._frame(carrier_id)
        self.assertAlmostEqual(sum(a * a for a in r), 1.0, places=5)
        self.assertAlmostEqual(sum(a * a for a in t), 1.0, places=5)
        self.assertAlmostEqual(sum(a * b for a, b in zip(r, t)), 0.0, places=5)

    def test_a_straight_in_approach_still_gets_a_usable_frame(self):
        # Nose pointed at the center: the tangential component of the heading is zero, so
        # the frame has to fall back rather than produce a zero vector.
        h = math.sqrt(0.5)
        self.ship.engine_object.rot_quat = sbs.quaternion(h, 0.0, -h, 0.0)
        carrier_id = ob.orbit_capture(self.ship_id, self.giant_id)
        r, t = self._frame(carrier_id)
        self.assertAlmostEqual(sum(a * a for a in t), 1.0, places=5)
        self.assertAlmostEqual(sum(a * b for a, b in zip(r, t)), 0.0, places=5)

    def test_the_orbit_keeps_the_plane_the_ship_arrived_on(self):
        # A ship sitting directly ABOVE the giant orbits through the pole, not snapped
        # flat onto the giant's XZ plane.
        high = to_object(player_spawn(0, 12000, 0, "Intrepid", "tsn",
                                      "tsn_battleship"))
        high.data_set.set("dock_state", "docked", 0)
        carrier_id = ob.orbit_capture(high.id, self.giant_id)
        r, _ = self._frame(carrier_id)
        self.assertAlmostEqual(r[1], 1.0, places=5)

    def test_the_circle_stays_at_radius_all_the_way_round(self):
        carrier_id = ob.orbit_capture(self.ship_id, self.giant_id)
        from sbs_utils.vec import Vec3
        from sbs_utils.procedural.inventory import get_inventory_value
        r, t = self._frame(carrier_id)
        radius = get_inventory_value(carrier_id, ob.ORBIT_KEY_RADIUS, 0.0)
        for i in range(24):
            p = ob._orbit_point(self.giant, radius, Vec3(*r), Vec3(*t),
                                (2.0 * math.pi * i) / 24.0)
            d = math.sqrt(p.x ** 2 + p.y ** 2 + p.z ** 2)
            self.assertAlmostEqual(d, radius, delta=0.5)


class TestCarrierPerformance(OrbitTestBase):
    def test_speed_is_written_not_inherited(self):
        # A stock hull tops out near 36 u/s, which would take ~26 minutes to lap this
        # orbit. The carrier is given the coefficient its circle actually needs.
        carrier_id = ob.orbit_capture(self.ship_id, self.giant_id, speed=200.0)
        ds = to_object(carrier_id).data_set
        self.assertAlmostEqual(ds.get("throttle", 0), 1.0, places=5)
        self.assertAlmostEqual(ds.get("speed_coeff", 0) * ob.ORBIT_BASE_TOP_SPEED,
                               200.0, places=3)

    def test_a_requested_period_sets_the_matching_speed(self):
        ob.orbit_capture(self.ship_id, self.giant_id, seconds=120.0)
        carrier_id = self._carrier()
        from sbs_utils.procedural.inventory import get_inventory_value
        speed = get_inventory_value(carrier_id, ob.ORBIT_KEY_SPEED, 0.0)
        self.assertAlmostEqual(speed, (2.0 * math.pi * 12000.0) / 120.0, delta=1.0)

    def test_turn_rate_keeps_the_carrier_out_of_its_own_braking_band(self):
        # Arrival braking bites within 2*(speed/turn_rate). If that reaches the aim point,
        # the carrier slows to a halt and the orbit dies - so it must stay inside the lead
        # distance the aim point is placed at.
        carrier_id = ob.orbit_capture(self.ship_id, self.giant_id, speed=200.0)
        ds = to_object(carrier_id).data_set
        brake_dist = 2.0 * (200.0 / ds.get("turn_rate", 0))
        lead_dist = 12000.0 * ob.ORBIT_LEAD_ANGLE
        self.assertLess(brake_dist, lead_dist)

    def test_the_carrier_is_aimed_ahead_of_itself(self):
        carrier_id = ob.orbit_capture(self.ship_id, self.giant_id)
        ds = to_object(carrier_id).data_set
        c = to_object(carrier_id)
        aim_dist = math.sqrt((ds.get("target_pos_x", 0) - c.pos.x) ** 2
                             + (ds.get("target_pos_y", 0) - c.pos.y) ** 2
                             + (ds.get("target_pos_z", 0) - c.pos.z) ** 2)
        self.assertGreater(aim_dist, 1.0)


class TestHelmFreeze(OrbitTestBase):
    def test_capture_stops_the_ship_being_driven(self):
        # Throttle is the lever that moves a ship; steering only points it. Holding the
        # throttle at zero is what makes it undrivable - the steering is taken over rather
        # than switched off, see the heading tests below.
        self.ship.data_set.set("playerThrottle", 1.0, 0)
        ob.orbit_capture(self.ship_id, self.giant_id)
        self.assertEqual(self.ship.data_set.get("playerThrottle", 0), 0)

    def test_capture_takes_the_steering_over(self):
        ob.orbit_capture(self.ship_id, self.giant_id)
        self.assertEqual(self.ship.data_set.get("steeringToDirFlag", 0), 1)

    def test_the_nose_is_pointed_along_the_orbit_not_at_the_body(self):
        # The whole point: the tractor holds POSITION and rotates nothing, so without this
        # the ship slides round the curve on whatever heading it arrived with.
        ob.orbit_capture(self.ship_id, self.giant_id)
        ds = self.ship.data_set
        heading = (ds.get("steerToDirDX", 0), ds.get("steerToDirDY", 0),
                   ds.get("steerToDirDZ", 0))
        self.assertAlmostEqual(sum(a * a for a in heading), 1.0, places=5)
        # Radial is +x here, so a tangent must have no radial component.
        self.assertAlmostEqual(heading[0], 0.0, places=5)

    def _put_carrier_at(self, carrier_id, degrees, radius=12000.0):
        """Move the carrier to a bearing on the circle. Radial is +x, tangent is +z here,
        so bearing b sits at (cos b, 0, sin b) * radius."""
        a = math.radians(degrees)
        to_object(carrier_id).pos = sbs.vec3(radius * math.cos(a), 0.0,
                                             radius * math.sin(a))

    def test_the_commanded_heading_follows_the_curve_round(self):
        # No physics runs in a unit test, so the carrier is walked round by hand - which is
        # the point: the heading must come from where it IS, not from the tick counter.
        carrier_id = ob.orbit_capture(self.ship_id, self.giant_id)
        ds = self.ship.data_set
        self._put_carrier_at(carrier_id, 0)
        ob.orbit_tick()
        first = (ds.get("steerToDirDX", 0), ds.get("steerToDirDZ", 0))
        self._put_carrier_at(carrier_id, 90)
        ob.orbit_tick()
        later = (ds.get("steerToDirDX", 0), ds.get("steerToDirDZ", 0))
        self.assertNotAlmostEqual(first[0], later[0], places=3)

    def test_the_heading_comes_from_where_the_carrier_IS_not_the_tick_count(self):
        # THE ENGINE BUG this exists to stop. Steering to the tangent at the tracked angle
        # aimed the nose systematically past the real direction of travel - measured 7-12
        # deg AHEAD of it, which reads as a ship drifting nose-out through the turn. The
        # tracked angle is left at ~0 here while the carrier sits at 90 deg; the commanded
        # heading must follow the carrier.
        carrier_id = ob.orbit_capture(self.ship_id, self.giant_id)
        self._put_carrier_at(carrier_id, 90)
        ob.orbit_tick()
        ds = self.ship.data_set
        # Tangent at bearing 90 (position +z) points along -x; at bearing 0 it points
        # along +z. Compare against both rather than against an exact -1: the lead loop
        # also fires on this tick, and how much lead it adds is not what is under test.
        dx = ds.get("steerToDirDX", 0)
        dz = ds.get("steerToDirDZ", 0)
        self.assertLess(dx, -0.5)          # decisively the bearing-90 tangent...
        self.assertLess(abs(dz), abs(dx))  # ...and not the bearing-0 one

    def test_the_heading_stays_near_the_tangent(self):
        # Not exactly perpendicular: the command is deliberately LED ahead of the tangent to
        # cover the hull's turn lag. What must hold is that it stays inside the lead clamp
        # of the TRUE tangent at the carrier's own bearing.
        carrier_id = ob.orbit_capture(self.ship_id, self.giant_id)
        ds = self.ship.data_set
        for deg in (0, 45, 90, 135, 180, 225, 270, 315):
            self._put_carrier_at(carrier_id, deg)
            ob.orbit_tick()
            a = math.radians(deg)
            radial = (math.cos(a), 0.0, math.sin(a))
            heading = (ds.get("steerToDirDX", 0), ds.get("steerToDirDY", 0),
                       ds.get("steerToDirDZ", 0))
            off = abs(sum(x * y for x, y in zip(radial, heading)))
            self.assertLessEqual(off, math.sin(ob.ORBIT_HEADING_LEAD_MAX) + 1e-6)

    def test_the_lead_grows_while_the_ship_lags_the_tangent(self):
        # The hull is pinned on one heading while the carrier travels, so it can never
        # catch up - the loop must keep raising its lead rather than settle short.
        from sbs_utils.procedural.inventory import get_inventory_value
        carrier_id = ob.orbit_capture(self.ship_id, self.giant_id)
        first = None
        for i in range(6):
            self.ship.engine_object.rot_quat = sbs.quaternion(1.0, 0.0, 0.0, 0.0)
            self._put_carrier_at(carrier_id, i * 15)
            ob.orbit_tick()
            if first is None:
                first = get_inventory_value(carrier_id, ob.ORBIT_KEY_LEAD, 0.0)
        last = get_inventory_value(carrier_id, ob.ORBIT_KEY_LEAD, 0.0)
        self.assertNotAlmostEqual(first, last, places=4)

    def test_the_lead_is_clamped(self):
        from sbs_utils.procedural.inventory import get_inventory_value
        carrier_id = ob.orbit_capture(self.ship_id, self.giant_id, speed=2000.0)
        for i in range(200):
            self.ship.engine_object.rot_quat = sbs.quaternion(1.0, 0.0, 0.0, 0.0)
            self._put_carrier_at(carrier_id, i * 7)
            ob.orbit_tick()
        lead = get_inventory_value(carrier_id, ob.ORBIT_KEY_LEAD, 0.0)
        self.assertLessEqual(abs(lead), ob.ORBIT_HEADING_LEAD_MAX + 1e-9)

    def test_release_hands_the_steering_back(self):
        ob.orbit_capture(self.ship_id, self.giant_id)
        ob.orbit_release(self.ship_id)
        self.assertEqual(self.ship.data_set.get("steeringToDirFlag", 0), 0)

    def test_the_tick_re_asserts_the_freeze(self):
        # Helm writes throttle too; holding a ship still is repeated, not done once.
        ob.orbit_capture(self.ship_id, self.giant_id)
        self.ship.data_set.set("playerThrottle", 1.0, 0)
        ob.orbit_tick()
        self.assertEqual(self.ship.data_set.get("playerThrottle", 0), 0)

    def test_warp_is_withdrawn_and_given_back(self):
        self.ship.data_set.set("warp", 1.0, 0)
        ob.orbit_capture(self.ship_id, self.giant_id)
        self.assertEqual(self.ship.data_set.get("warp", 0), 0)
        ob.orbit_release(self.ship_id)
        self.assertAlmostEqual(self.ship.data_set.get("warp", 0), 1.0, places=5)


class TestTick(OrbitTestBase):
    def test_the_angle_advances(self):
        from sbs_utils.procedural.inventory import get_inventory_value
        carrier_id = ob.orbit_capture(self.ship_id, self.giant_id, speed=200.0)
        ob.orbit_tick()
        angle = get_inventory_value(carrier_id, ob.ORBIT_KEY_ANGLE, 0.0)
        self.assertAlmostEqual(angle, (200.0 / 12000.0) * ob.ORBIT_TICK_SECONDS, places=6)

    def test_the_aim_point_stays_near_the_circle(self):
        # Not ON it: the corrector pushes the aim point out so the FLOWN path lands on the
        # circle. What must hold is that the correction stays inside its clamp instead of
        # wandering off - an aim point that ran away would take the ship with it.
        carrier_id = ob.orbit_capture(self.ship_id, self.giant_id, speed=200.0)
        for _ in range(10):
            ob.orbit_tick()
            ds = to_object(carrier_id).data_set
            d = math.sqrt(ds.get("target_pos_x", 0) ** 2
                          + ds.get("target_pos_y", 0) ** 2
                          + ds.get("target_pos_z", 0) ** 2)
            self.assertGreaterEqual(d, 12000.0 * ob.ORBIT_AIM_MIN - 1.0)
            self.assertLessEqual(d, 12000.0 * ob.ORBIT_AIM_MAX + 1.0)

    def test_the_integrator_keeps_pushing_on_a_persistent_sag(self):
        # The ENGINE failure this exists to stop: with a proportional term only, a constant
        # inward bias leaves constant standing error and the orbit spirals (measured
        # 8997 -> 8759 over 75s in real Cosmos, no settle). The integrator must keep
        # raising its correction while the error persists.
        carrier_id = ob.orbit_capture(self.ship_id, self.giant_id, speed=200.0)
        carrier = to_object(carrier_id)
        carrier.pos = sbs.vec3(11500, 0, 0)          # 500u inside, and it stays there
        first = ob._orbit_aim_radius(carrier_id, self.giant, 12000.0)
        for _ in range(5):
            carrier.pos = sbs.vec3(11500, 0, 0)
            later = ob._orbit_aim_radius(carrier_id, self.giant, 12000.0)
        self.assertGreater(later, first)

    def test_the_integrator_is_clamped(self):
        # Anti-windup: a long-held error must not build a correction that then takes a
        # whole lap to unwind.
        carrier_id = ob.orbit_capture(self.ship_id, self.giant_id, speed=200.0)
        carrier = to_object(carrier_id)
        for _ in range(500):
            carrier.pos = sbs.vec3(1000, 0, 0)       # absurdly far inside, held
            aim = ob._orbit_aim_radius(carrier_id, self.giant, 12000.0)
        self.assertLessEqual(aim, 12000.0 * ob.ORBIT_AIM_MAX + 1.0)

    def test_asking_where_it_would_aim_does_not_move_the_integrator(self):
        carrier_id = ob.orbit_capture(self.ship_id, self.giant_id, speed=200.0)
        carrier = to_object(carrier_id)
        carrier.pos = sbs.vec3(11500, 0, 0)
        a = ob._orbit_aim_radius(carrier_id, self.giant, 12000.0, accumulate=False)
        b = ob._orbit_aim_radius(carrier_id, self.giant, 12000.0, accumulate=False)
        self.assertAlmostEqual(a, b, places=6)

    def test_the_corrector_pushes_the_aim_out_when_the_carrier_sags_inward(self):
        # The measured failure this exists to stop: uncorrected pursuit settled 8.7% inside
        # the commanded circle, which put the ship inside the body's exclusion radius.
        carrier_id = ob.orbit_capture(self.ship_id, self.giant_id, speed=200.0)
        carrier = to_object(carrier_id)
        carrier.pos = sbs.vec3(11000, 0, 0)          # 1000u inside the circle
        aim = ob._orbit_aim_radius(carrier_id, self.giant, 12000.0)
        self.assertGreater(aim, 12000.0)

    def test_undocking_releases_the_orbit(self):
        # The `undocking` section only runs on the engine's docking_change event, so the
        # tick is the backstop for every other way a dock ends.
        ob.orbit_capture(self.ship_id, self.giant_id)
        self.ship.data_set.set("dock_state", "undocked", 0)
        ob.orbit_tick()
        self.assertFalse(ob.orbit_is(self.ship_id))
        self.assertEqual(ob.orbit_count(), 0)

    def test_a_vanished_center_releases_the_orbit(self):
        ob.orbit_capture(self.ship_id, self.giant_id)
        self.giant.delete_object()
        ob.orbit_tick()
        self.assertFalse(ob.orbit_is(self.ship_id))

    def test_a_vanished_ship_drops_the_carrier(self):
        carrier_id = ob.orbit_capture(self.ship_id, self.giant_id)
        self.ship.delete_object()
        ob.orbit_tick()
        self.assertFalse(object_exists(carrier_id))
        self.assertEqual(ob.orbit_count(), 0)


class TestRelease(OrbitTestBase):
    def test_release_removes_everything(self):
        carrier_id = ob.orbit_capture(self.ship_id, self.giant_id)
        self.assertTrue(ob.orbit_release(self.ship_id))
        self.assertFalse(self._connected(carrier_id, self.ship_id))
        self.assertFalse(object_exists(carrier_id))
        self.assertFalse(ob.orbit_is(self.ship_id))
        self.assertEqual(len(role(ob.ORBIT_CARRIER_ROLE)), 0)
        self.assertEqual(ob.orbit_count(), 0)

    def test_release_of_a_free_ship_is_a_no_op(self):
        self.assertFalse(ob.orbit_release(self.ship_id))

    def test_release_does_not_delete_the_ship(self):
        # The reason this is not built on mount.py: delete_with_host would take the ship.
        ob.orbit_capture(self.ship_id, self.giant_id)
        ob.orbit_release(self.ship_id)
        self.assertTrue(object_exists(self.ship_id))

    def test_release_all_clears_every_orbit(self):
        other = to_object(player_spawn(0, 0, 12000, "Intrepid", "tsn",
                                       "tsn_battleship"))
        other.data_set.set("dock_state", "docked", 0)
        ob.orbit_capture(self.ship_id, self.giant_id)
        ob.orbit_capture(other.id, self.giant_id)
        self.assertEqual(ob.orbit_count(), 2)
        ob.orbit_release_all()
        self.assertEqual(ob.orbit_count(), 0)
        self.assertEqual(len(role(ob.ORBIT_CARRIER_ROLE)), 0)

    def test_a_destroyed_ship_releases_in_the_destroy_handler(self):
        carrier_id = ob.orbit_capture(self.ship_id, self.giant_id)
        ob._orbit_on_destroy(self.ship_id)
        self.assertFalse(ob.orbit_is(self.ship_id))
        self.assertFalse(object_exists(carrier_id))

    def test_a_destroyed_carrier_frees_the_ship(self):
        carrier_id = ob.orbit_capture(self.ship_id, self.giant_id)
        ob._orbit_on_destroy(carrier_id)
        self.assertFalse(ob.orbit_is(self.ship_id))
        self.assertTrue(object_exists(self.ship_id))


class TestQueries(OrbitTestBase):
    def test_queries_are_none_when_not_orbiting(self):
        self.assertIsNone(ob.orbit_carrier_of(self.ship_id))
        self.assertIsNone(ob.orbit_center_of(self.ship_id))
        self.assertIsNone(ob.orbit_radius_of(self.ship_id))
        self.assertFalse(ob.orbit_is(self.ship_id))

    def test_a_deleted_carrier_reads_as_not_orbiting(self):
        # A link can outlive the object it points at; handing back a dangling id is the
        # use-after-free trap.
        carrier_id = ob.orbit_capture(self.ship_id, self.giant_id)
        to_object(carrier_id).delete_object()
        self.assertIsNone(ob.orbit_carrier_of(self.ship_id))
        self.assertFalse(ob.orbit_is(self.ship_id))


if __name__ == "__main__":
    unittest.main()
