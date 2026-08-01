"""Camera API - the set-addressed wrapper over the engine's one cinematic call."""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

from cosmos_dev.mock import sbs as mock_sbs
from sbs_utils.helpers import FrameContext, Context
from sbs_utils.spaceobject import SpaceObject
from sbs_utils.vec import Vec3
from sbs_utils.procedural.gui.camera import (camera_anchor, camera_assign, camera_track,
                                             camera_auto, camera_orbit_eye, camera_shot)
from sbs_utils.procedural.query import to_object


class FakeEvent:
    client_id = 0
    tag = ""
    sub_tag = ""
    origin_id = 0
    selected_id = 0
    parent_id = 0
    value_tag = ""
    extra_tag = ""
    extra_extra_tag = ""
    sub_float = 0.0
    source_point = None
    event_time = 0


# Console ids carry the client bit (0x8000...); a small int is not a console and
# consoles_of() correctly resolves it to nothing. Use real-shaped ids.
C1 = 0x8000000000000001
C2 = 0x8000000000000002
C3 = 0x8000000000000003


class TestCamera(unittest.TestCase):
    def setUp(self):
        mock_sbs.create_new_sim()
        SpaceObject.clear()
        # create_new_sim() does NOT clear the mock's per-client cinematic state, so a camera
        # set by an earlier test survives into this one. Worth knowing beyond the tests: a
        # mission restart leaves each client pointed at a dolly id from the PREVIOUS sim.
        mock_sbs._cinematic.clear()
        FrameContext.context = Context(mock_sbs.sim, mock_sbs, FakeEvent())

    # --- the anchor -------------------------------------------------------
    def test_anchor_is_invisible_and_not_a_player(self):
        """It has to be player-family so a client can be ASSIGNED to it, invisible so it never
        appears in the shot, and NOT __player__ so it is not counted as a player ship."""
        cam = camera_anchor(10, 20, 30)
        self.assertTrue(cam)
        obj = to_object(cam)
        self.assertIsNotNone(obj)
        self.assertFalse(obj.has_role("__player__"))
        self.assertEqual(mock_sbs.sim.get_space_object(cam)._data_tag, "invisible")

    def test_anchor_lands_where_asked(self):
        obj = to_object(camera_anchor(100, 200, 300))
        self.assertAlmostEqual(obj.pos.x, 100, places=3)
        self.assertAlmostEqual(obj.pos.y, 200, places=3)
        self.assertAlmostEqual(obj.pos.z, 300, places=3)

    # --- tracking ---------------------------------------------------------
    def test_track_points_the_named_client(self):
        cam = camera_anchor(0, 0, 0)
        n = camera_track(C1, cam, eye=(0, 500, -1200))
        self.assertEqual(n, 1)
        state = mock_sbs._cinematic.get(C1)
        self.assertIsNotNone(state)
        self.assertEqual(state["script"], 1)
        self.assertEqual(state["dolly_id"], cam)
        self.assertEqual(state["dolly_off"], (0.0, 500.0, -1200.0))

    def test_target_defaults_to_the_dolly(self):
        """A single-subject shot pins BOTH ids to that object - the shape the engine wants."""
        cam = camera_anchor(0, 0, 0)
        camera_track(C2, cam)
        state = mock_sbs._cinematic.get(C2)
        self.assertEqual(state["dolly_id"], state["target_id"])

    def test_two_object_request_is_folded_into_one(self):
        """The engine only renders when dolly == target, so a two-object shot is re-expressed
        as one object plus an offset - keeping the lens exactly where the caller put it."""
        cam = camera_anchor(0, 0, 0)
        subject = camera_anchor(5000, 0, 0)
        camera_track(C3, cam, eye=Vec3(0, 100, -400), target=subject)
        state = mock_sbs._cinematic.get(C3)
        self.assertEqual(state["dolly_id"], state["target_id"])   # one object, as required
        self.assertEqual(state["target_id"], subject)             # the SUBJECT is kept
        # lens was cam(0,0,0)+(0,100,-400); as an offset from subject(5000,0,0) that is:
        self.assertEqual(state["dolly_off"], (-5000.0, 100.0, -400.0))

    def test_track_fans_out_over_a_set(self):
        """The reason this module exists: the engine call takes one client id."""
        cam = camera_anchor(0, 0, 0)
        n = camera_track({C1, C2, C3}, cam)
        self.assertEqual(n, 3)
        for cid in (C1, C2, C3):
            self.assertEqual(mock_sbs._cinematic[cid]["dolly_id"], cam)

    def test_track_assigns_the_console_to_the_dolly(self):
        """Engine-observed: a camera change only takes when the console is assigned to the
        object the lens rides. Re-pointing alone was a black screen. The two are one
        operation - and yes, that means moving the camera changes what the console can see,
        because culling follows the assigned object."""
        cam = camera_anchor(0, 0, 0)
        camera_track(C1, cam)
        self.assertEqual(mock_sbs.sim.client_ships.get(C1), cam)

    def test_track_with_no_dolly_is_a_no_op(self):
        self.assertEqual(camera_track(C1, None), 0)
        self.assertIsNone(mock_sbs._cinematic.get(C1))

    # --- assignment -------------------------------------------------------
    def test_assign_puts_the_console_on_the_object(self):
        cam = camera_anchor(0, 0, 0)
        n = camera_assign({C1, C2}, cam)
        self.assertEqual(n, 2)
        self.assertEqual(mock_sbs.sim.client_ships.get(C1), cam)
        self.assertEqual(mock_sbs.sim.client_ships.get(C2), cam)

    # --- release ----------------------------------------------------------
    def test_auto_releases_script_control(self):
        cam = camera_anchor(0, 0, 0)
        camera_track(C1, cam)
        self.assertEqual(mock_sbs._cinematic[C1]["script"], 1)
        camera_auto(C1)
        self.assertEqual(mock_sbs._cinematic[C1]["script"], 0)

    # --- the degenerate pin -----------------------------------------------
    def test_degenerate_pin_is_detected(self):
        """Camera exactly on its own look-at point: normalize(target-eye) divides by zero, so
        the engine draws a BLACK frame with nothing logged. Easy to ask for by accident, since
        `target` defaults to the dolly and `eye` defaults to no offset."""
        from sbs_utils.procedural.gui.camera import _degenerate
        cam = camera_anchor(0, 0, 0)
        zero = Vec3(0, 0, 0)
        self.assertTrue(_degenerate(cam, zero, cam, zero))
        self.assertFalse(_degenerate(cam, Vec3(0, 400, -900), cam, zero))

    def test_degenerate_across_two_objects_at_one_place(self):
        """Two different objects sharing a position is the same failure wearing a disguise."""
        from sbs_utils.procedural.gui.camera import _degenerate
        a = camera_anchor(500, 0, 0)
        b = camera_anchor(500, 0, 0)
        self.assertTrue(_degenerate(a, Vec3(0, 0, 0), b, Vec3(0, 0, 0)))
        self.assertFalse(_degenerate(a, Vec3(0, 300, 0), b, Vec3(0, 0, 0)))

    def test_degenerate_pin_is_nudged_not_emitted(self):
        """We never hand the engine a zero-length view vector - it just draws black."""
        cam = camera_anchor(0, 0, 0)
        camera_track(C1, cam)                     # no eye offset, target defaults to the dolly
        off = mock_sbs._cinematic[C1]["dolly_off"]
        self.assertNotEqual(off, (0.0, 0.0, 0.0))

    def test_shot_places_the_lens_at_a_world_position(self):
        """camera_shot composes 'lens here, looking at that' out of the one-object shape the
        engine accepts: same id twice, with the offset doing the placing."""
        subj = camera_anchor(1000, 0, 500)
        camera_shot(C2, subj, Vec3(1000, 900, -2100))
        st = mock_sbs._cinematic[C2]
        self.assertEqual(st["dolly_id"], st["target_id"])          # one object, named twice
        self.assertEqual(st["dolly_off"], (0.0, 900.0, -2600.0))   # wanted - subject.pos

    # --- orbit geometry ---------------------------------------------------
    def test_orbit_eye_zero_yaw_is_straight_back(self):
        v = camera_orbit_eye(1000)
        self.assertAlmostEqual(v.x, 0, places=3)
        self.assertAlmostEqual(v.z, 1000, places=3)

    def test_orbit_eye_yaw_90_swings_to_the_side(self):
        """The Game Master's formula: orbiting is rotating the OFFSET, because the engine does
        not rotate offsets into the dolly's frame."""
        v = camera_orbit_eye(1000, yaw=90)
        self.assertAlmostEqual(abs(v.x), 1000, places=2)
        self.assertAlmostEqual(v.z, 0, places=2)

    def test_orbit_eye_keeps_its_distance(self):
        for yaw in (0, 37, 90, 180, 305):
            v = camera_orbit_eye(750, yaw=yaw, pitch=15)
            self.assertAlmostEqual((v.x * v.x + v.y * v.y + v.z * v.z) ** 0.5, 750, places=2)


if __name__ == "__main__":
    unittest.main()
