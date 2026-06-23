from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

from cosmos_dev.mock import sbs
import math
import unittest


def _make_obj():
    return sbs.sim.create_space_object("ACTIVE", "test", 0)


class TestMockSbs(unittest.TestCase):

    def setUp(self):
        sbs.create_new_sim()

    # ------------------------------------------------------------------
    # delete_object
    # ------------------------------------------------------------------

    def test_delete_object_removes_from_space_objects(self):
        obj_id = _make_obj()
        self.assertIn(obj_id, sbs.sim.space_objects)
        sbs.delete_object(obj_id)
        self.assertNotIn(obj_id, sbs.sim.space_objects)

    def test_delete_nonexistent_object_is_noop(self):
        sbs.delete_object(999_999_999)   # must not raise

    # ------------------------------------------------------------------
    # assign_client_to_ship / get_ship_of_client
    # ------------------------------------------------------------------

    def test_assign_client_to_ship_roundtrip(self):
        obj_id = _make_obj()
        sbs.assign_client_to_ship(5, obj_id)
        self.assertEqual(sbs.get_ship_of_client(5), obj_id)

    def test_unassign_client_with_zero(self):
        obj_id = _make_obj()
        sbs.assign_client_to_ship(5, obj_id)
        sbs.assign_client_to_ship(5, 0)
        self.assertEqual(sbs.get_ship_of_client(5), 0)

    def test_get_ship_of_client_unassigned_returns_zero(self):
        self.assertEqual(sbs.get_ship_of_client(99), 0)

    # ------------------------------------------------------------------
    # get_client_ID_list
    # ------------------------------------------------------------------

    def test_get_client_id_list_reflects_assignments(self):
        id1, id2, id3 = _make_obj(), _make_obj(), _make_obj()
        sbs.assign_client_to_ship(1, id1)
        sbs.assign_client_to_ship(2, id2)
        sbs.assign_client_to_ship(3, id3)
        result = sbs.get_client_ID_list()
        self.assertIn(1, result)
        self.assertIn(2, result)
        self.assertIn(3, result)

    def test_get_client_id_list_excludes_unknown_clients(self):
        sbs.assign_client_to_ship(7, _make_obj())
        self.assertNotIn(99, sbs.get_client_ID_list())

    def test_get_client_id_list_empty_after_create_new_sim(self):
        sbs.assign_client_to_ship(1, _make_obj())
        sbs.create_new_sim()
        self.assertEqual(sbs.get_client_ID_list(), [])

    # ------------------------------------------------------------------
    # assign_client_to_alt_ship
    # ------------------------------------------------------------------

    def test_assign_client_to_alt_ship(self):
        obj_id = _make_obj()
        sbs.assign_client_to_alt_ship(3, obj_id)
        self.assertEqual(sbs.sim.client_alt_ships.get(3), obj_id)

    def test_unassign_client_alt_ship_with_zero(self):
        sbs.assign_client_to_alt_ship(3, _make_obj())
        sbs.assign_client_to_alt_ship(3, 0)
        self.assertNotIn(3, sbs.sim.client_alt_ships)

    # ------------------------------------------------------------------
    # standby list
    # ------------------------------------------------------------------

    def test_push_to_standby_removes_from_space_objects(self):
        obj_id = _make_obj()
        sbs.push_to_standby_list_id(obj_id)
        self.assertNotIn(obj_id, sbs.sim.space_objects)

    def test_in_standby_list_id_true_after_push(self):
        obj_id = _make_obj()
        sbs.push_to_standby_list_id(obj_id)
        self.assertTrue(sbs.in_standby_list_id(obj_id))

    def test_in_standby_list_id_false_before_push(self):
        obj_id = _make_obj()
        self.assertFalse(sbs.in_standby_list_id(obj_id))

    def test_object_in_standby_not_in_space(self):
        obj_id = _make_obj()
        sbs.push_to_standby_list_id(obj_id)
        self.assertNotIn(obj_id, sbs.sim.space_objects)
        self.assertIn(obj_id, sbs.sim.standby_list)

    def test_retrieve_from_standby_restores_to_space_objects(self):
        obj_id = _make_obj()
        sbs.push_to_standby_list_id(obj_id)
        sbs.retrieve_from_standby_list_id(obj_id)
        self.assertIn(obj_id, sbs.sim.space_objects)

    def test_retrieve_from_standby_removes_from_standby_list(self):
        obj_id = _make_obj()
        sbs.push_to_standby_list_id(obj_id)
        sbs.retrieve_from_standby_list_id(obj_id)
        self.assertFalse(sbs.in_standby_list_id(obj_id))

    # ------------------------------------------------------------------
    # client console type tracking
    # ------------------------------------------------------------------

    def test_get_type_of_client_default_is_mainscreen(self):
        self.assertEqual(sbs.get_type_of_client(99), "mainscreen")

    def test_send_client_widget_list_sets_console_type(self):
        sbs.send_client_widget_list(1, "helm", "")
        self.assertEqual(sbs.get_type_of_client(1), "helm")

    def test_send_client_widget_list_empty_type_does_not_overwrite(self):
        sbs.send_client_widget_list(1, "weapons", "")
        sbs.send_client_widget_list(1, "", "")   # empty type — must not overwrite
        self.assertEqual(sbs.get_type_of_client(1), "weapons")

    def test_send_client_widget_list_can_reassign_type(self):
        sbs.send_client_widget_list(2, "science", "")
        sbs.send_client_widget_list(2, "engineering", "")
        self.assertEqual(sbs.get_type_of_client(2), "engineering")

    # ------------------------------------------------------------------
    # side relationships
    # ------------------------------------------------------------------

    def test_side_relationship_hostile(self):
        sbs.sim.set_side_relationship("tsn", "raider", int(sbs.DIPLOMACY.HOSTILE))
        self.assertEqual(
            sbs.sim.get_side_relationship("tsn", "raider"),
            int(sbs.DIPLOMACY.HOSTILE),
        )

    def test_side_relationship_is_symmetric(self):
        sbs.sim.set_side_relationship("tsn", "raider", int(sbs.DIPLOMACY.HOSTILE))
        self.assertEqual(
            sbs.sim.get_side_relationship("raider", "tsn"),
            int(sbs.DIPLOMACY.HOSTILE),
        )

    def test_side_relationship_default_neutral(self):
        self.assertEqual(
            sbs.sim.get_side_relationship("tsn", "unknown_side"),
            int(sbs.DIPLOMACY.NEUTRAL),
        )

    def test_side_relationship_can_be_updated(self):
        sbs.sim.set_side_relationship("tsn", "raider", int(sbs.DIPLOMACY.HOSTILE))
        sbs.sim.set_side_relationship("tsn", "raider", int(sbs.DIPLOMACY.ALLIED))
        self.assertEqual(
            sbs.sim.get_side_relationship("tsn", "raider"),
            int(sbs.DIPLOMACY.ALLIED),
        )

    # ------------------------------------------------------------------
    # navpoint distance computation
    # ------------------------------------------------------------------

    def test_distance_between_navpoints_3_4_5(self):
        id1 = sbs.sim.add_navpoint(0, 0, 0, "origin", "white")
        id2 = sbs.sim.add_navpoint(3, 0, 4, "far", "white")
        self.assertAlmostEqual(sbs.distance_between_navpoints(id1, id2), 5.0, places=5)

    def test_distance_between_navpoints_same_point_is_zero(self):
        id1 = sbs.sim.add_navpoint(100, 200, 300, "a", "white")
        id2 = sbs.sim.add_navpoint(100, 200, 300, "b", "white")
        self.assertAlmostEqual(sbs.distance_between_navpoints(id1, id2), 0.0, places=5)

    def test_distance_between_navpoints_missing_id_returns_fallback(self):
        self.assertEqual(sbs.distance_between_navpoints(9_999_001, 9_999_002), 1000.0)

    def test_distance_to_navpoint_3_4_5(self):
        nav_id = sbs.sim.add_navpoint(0, 0, 0, "origin", "white")
        obj_id = sbs.sim.create_space_object("ACTIVE", "test", 0)
        obj = sbs.sim.space_objects[obj_id]
        obj.pos.x = 3
        obj.pos.y = 0
        obj.pos.z = 4
        self.assertAlmostEqual(sbs.distance_to_navpoint(nav_id, obj_id), 5.0, places=5)

    def test_distance_to_navpoint_missing_returns_fallback(self):
        self.assertEqual(sbs.distance_to_navpoint(9_999_001, 9_999_002), 1000.0)

    # ------------------------------------------------------------------
    # navareas
    # ------------------------------------------------------------------

    def test_add_navarea_stores_corners_text_color(self):
        aid = sbs.sim.add_navarea(0, 0, 5000, 0, 5000, 5000, 0, 5000, "Zone", "#f80")
        area = sbs.sim.get_navpoint_by_id(aid)
        self.assertIsInstance(area, sbs.navarea)
        self.assertEqual(area._points, [(0, 0), (5000, 0), (5000, 5000), (0, 5000)])
        self.assertEqual(area.text, "Zone")
        self.assertEqual(area.color, "#f80")

    def test_navarea_is_a_navpoint_with_navpoint_properties(self):
        aid = sbs.sim.add_navarea(0, 0, 5000, 0, 5000, 5000, 0, 5000, "Zone", "#f80")
        self.assertTrue(sbs.sim.navpoint_exists(aid))
        area = sbs.sim.get_navpoint_by_id(aid)
        self.assertIsInstance(area, sbs.navpoint)
        # centroid position, and standard navpoint properties are settable
        self.assertAlmostEqual(area.pos.x, 2500.0)
        self.assertAlmostEqual(area.pos.z, 2500.0)
        area.visibleToShip = 1234
        area.visibleToSide = "tsn"
        self.assertEqual(area.visibleToShip, 1234)
        self.assertEqual(area.visibleToSide, "tsn")

    def test_add_navarea_ids_are_unique(self):
        a1 = sbs.sim.add_navarea(0, 0, 1, 0, 1, 1, 0, 1, "A", "white")
        a2 = sbs.sim.add_navarea(0, 0, 1, 0, 1, 1, 0, 1, "B", "white")
        self.assertNotEqual(a1, a2)

    def test_delete_navpoint_by_id_removes_navarea(self):
        aid = sbs.sim.add_navarea(0, 0, 1, 0, 1, 1, 0, 1, "A", "white")
        sbs.sim.delete_navpoint_by_id(aid)
        self.assertFalse(sbs.sim.navpoint_exists(aid))

    def test_delete_all_navpoints_clears_navareas(self):
        aid = sbs.sim.add_navarea(0, 0, 1, 0, 1, 1, 0, 1, "A", "white")
        sbs.delete_all_navpoints()
        self.assertIsNone(sbs.sim.get_navpoint_by_id(aid))

    # ------------------------------------------------------------------
    # NPC / player movement physics
    # ------------------------------------------------------------------

    def _spawn_npc(self, behave="behav_npcship", **ds_kw):
        sid = sbs.sim.create_space_object(behave, "test", 0x10)
        o = sbs.sim.space_objects[sid]
        o._pos = sbs.vec3(0, 0, 0)
        params = {"throttle": 1.0, "speed_coeff": 1.0, "turn_rate": 1.0,
                  "target_pos_x": 0.0, "target_pos_z": 100000.0}
        params.update(ds_kw)
        for k, v in params.items():
            o.data_set.set(k, v)
        sbs.resume_sim()
        return o

    def _tick(self, n=1, dt=1.0):
        for _ in range(n):
            sbs.physics_tick(dt=dt)

    def test_npc_moves_forward_toward_far_target(self):
        o = self._spawn_npc()                 # target straight ahead on +z
        self._tick(6)
        self.assertGreater(o._pos.z, 100.0)   # advanced down +z
        self.assertGreater(o._cur_speed, 0.0)

    def test_npc_zero_throttle_does_not_move(self):
        o = self._spawn_npc(throttle=0.0)
        self._tick(6)
        self.assertAlmostEqual(o._pos.z, 0.0)
        self.assertEqual(o._cur_speed, 0.0)

    def test_speed_coeff_is_a_multiplier_on_top_speed(self):
        o = self._spawn_npc(speed_coeff=0.5)
        self._tick(10)                        # long enough to reach cruise
        self.assertAlmostEqual(o._cur_speed, 0.5 * sbs.BASE_TOP_SPEED)

    def test_total_speed_coeff_takes_priority_over_speed_coeff(self):
        o = self._spawn_npc(speed_coeff=1.0)
        o.data_set.set("total_speed_coeff", 0.25)
        self._tick(10)
        self.assertAlmostEqual(o._cur_speed, 0.25 * sbs.BASE_TOP_SPEED)

    def test_speed_ramps_and_does_not_snap(self):
        o = self._spawn_npc()
        self._tick(1, dt=1.0)
        # after one second the ship has only ramped by SPEED_RAMP_RATE, not jumped
        # to full cruise speed.
        self.assertAlmostEqual(o._cur_speed, sbs.SPEED_RAMP_RATE)
        self.assertLess(o._cur_speed, sbs.BASE_TOP_SPEED)

    def test_npc_brakes_and_parks_at_near_target_no_orbit(self):
        # Target inside the turn radius used to make the ship orbit forever.
        o = self._spawn_npc(target_pos_x=0.0, target_pos_z=150.0)
        self._tick(40)
        self.assertEqual(o._cur_speed, 0.0)               # stopped, not circling
        dist = math.hypot(0.0 - o._pos.x, 150.0 - o._pos.z)
        self.assertLessEqual(dist, 25.0)                  # parked at the target

    def test_death_state_halts_npc(self):
        o = self._spawn_npc()
        self._tick(4)
        self.assertGreater(o._cur_speed, 0.0)
        o.data_set.set("deathState", 1)
        self._tick(1)
        self.assertEqual(o._cur_speed, 0.0)

    def test_player_ship_moves_from_player_throttle(self):
        o = self._spawn_npc(behave="behav_playership")
        o.data_set.set("playerThrottle", 1.0)
        self._tick(8)
        self.assertGreater(o._pos.z, 100.0)
        self.assertAlmostEqual(o._cur_speed, sbs.BASE_TOP_SPEED)

    def test_player_warp_is_faster_than_full_impulse(self):
        o = self._spawn_npc(behave="behav_playership")
        o.data_set.set("playerThrottle", 2.0)             # >1.0 = warp
        self._tick(60)
        self.assertGreater(o._cur_speed, sbs.BASE_TOP_SPEED)

    def test_player_zero_throttle_does_not_move(self):
        o = self._spawn_npc(behave="behav_playership")
        o.data_set.set("playerThrottle", 0.0)
        self._tick(6)
        self.assertAlmostEqual(o._pos.z, 0.0)
        self.assertEqual(o._cur_speed, 0.0)

    # ------------------------------------------------------------------
    # create_new_sim resets all tracked state
    # ------------------------------------------------------------------

    def test_create_new_sim_clears_space_objects(self):
        _make_obj()
        _make_obj()
        sbs.create_new_sim()
        self.assertEqual(len(sbs.sim.space_objects), 0)

    def test_create_new_sim_resets_client_ships(self):
        sbs.assign_client_to_ship(5, _make_obj())
        sbs.create_new_sim()
        self.assertEqual(sbs.get_client_ID_list(), [])

    def test_create_new_sim_resets_standby_list(self):
        obj_id = _make_obj()
        sbs.push_to_standby_list_id(obj_id)
        sbs.create_new_sim()
        self.assertFalse(sbs.in_standby_list_id(obj_id))

    def test_create_new_sim_resets_side_relations(self):
        sbs.sim.set_side_relationship("tsn", "raider", int(sbs.DIPLOMACY.HOSTILE))
        sbs.create_new_sim()
        self.assertEqual(
            sbs.sim.get_side_relationship("tsn", "raider"),
            int(sbs.DIPLOMACY.NEUTRAL),
        )


if __name__ == "__main__":
    unittest.main()
