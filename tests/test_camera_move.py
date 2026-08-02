"""Phase 2 — the mover.

"Camera animation" is a misnomer: the engine interpolates nothing, so a move is a
driver that RE-AIMS the shot every tick. Two engine facts shape all of it — offsets
are WORLD-space (so an orbit recomputes the offset rather than rotating a local
frame), and dolly must equal target (so a move animates the LENS around a subject;
there is no second object to fly).

These tests drive the mock's `_cinematic` state, which is what the engine call
actually sets, rather than asserting that our own functions were called.
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest

from cosmos_dev.mock import sbs as mock_sbs
from sbs_utils.helpers import FrameContext, Context
from sbs_utils.spaceobject import SpaceObject
from sbs_utils.tickdispatcher import TickDispatcher
from sbs_utils.vec import Vec3
from sbs_utils.procedural.gui.camera import (
    camera_anchor, camera_move, camera_orbit, camera_rack, camera_move_stop,
    camera_eye, camera_shot, _ease, _MOVES)


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


C1 = 0x8000000000000001
C2 = 0x8000000000000002


class MoveBase(unittest.TestCase):
    def setUp(self):
        mock_sbs.create_new_sim()
        SpaceObject.clear()
        TickDispatcher.clear()
        mock_sbs._cinematic.clear()
        _MOVES.clear()
        FrameContext.context = Context(mock_sbs.sim, mock_sbs, FakeEvent())

    def tearDown(self):
        TickDispatcher.clear()
        _MOVES.clear()
        FrameContext.context = None

    def advance(self, seconds):
        """Run the tick clock forward by sim seconds."""
        from cosmos_dev.mock.sbs import TICKS_PER_SECOND
        for _ in range(int(seconds * TICKS_PER_SECOND) + 1):
            TickDispatcher.dispatch_tick()
            mock_sbs.sim._time_tick_counter += 1

    def eye_of(self, cid):
        """Where the lens actually is, per the engine call: the dolly's position
        plus the world-space offset it was given."""
        state = mock_sbs._cinematic.get(cid)
        if state is None:
            return None
        obj = mock_sbs.sim.get_space_object(state["dolly_id"])
        off = state["dolly_off"]
        return Vec3(obj.pos.x + off[0], obj.pos.y + off[1], obj.pos.z + off[2])


class TestEase(MoveBase):
    """Ours, because the engine has none."""

    def test_endpoints_are_exact(self):
        for name in ("linear", "in", "out", "in_out"):
            self.assertEqual(_ease(name, 0.0), 0.0, name)
            self.assertEqual(_ease(name, 1.0), 1.0, name)

    def test_it_is_monotonic(self):
        for name in ("linear", "in", "out", "in_out"):
            prev = -1.0
            for i in range(21):
                v = _ease(name, i / 20.0)
                self.assertGreaterEqual(v, prev, f"{name} went backwards")
                prev = v

    def test_in_starts_slow_and_out_starts_fast(self):
        self.assertLess(_ease("in", 0.25), 0.25)
        self.assertGreater(_ease("out", 0.25), 0.25)

    def test_an_unknown_name_is_linear_not_an_error(self):
        # A typo in a style-ish string should not kill a cutscene mid-shot.
        self.assertAlmostEqual(_ease("wobble", 0.5), 0.5)


class TestMove(MoveBase):
    def test_the_lens_travels_from_a_to_b(self):
        subj = camera_anchor(0, 0, 0)
        camera_move(C1, subj, Vec3(0, 0, -4000), Vec3(0, 0, -1000), 4.0,
                    ease="linear")
        start = self.eye_of(C1)
        self.assertAlmostEqual(start.z, -4000, places=0)
        self.advance(2.0)
        mid = self.eye_of(C1)
        self.assertGreater(mid.z, -4000)
        self.assertLess(mid.z, -1000)
        self.advance(3.0)
        self.assertAlmostEqual(self.eye_of(C1).z, -1000, places=0)

    def test_it_resolves_when_it_arrives(self):
        subj = camera_anchor(0, 0, 0)
        prom = camera_move(C1, subj, (0, 0, -2000), (0, 0, -500), 3.0)
        self.advance(1.0)
        self.assertFalse(prom.done(), "resolved before it arrived")
        self.advance(3.0)
        self.assertTrue(prom.done())

    def test_it_always_lands_exactly_on_the_end(self):
        # Clamped, so a tick that overshoots the duration cannot leave the shot
        # slightly past its mark - which would read as a camera that drifts.
        subj = camera_anchor(0, 0, 0)
        camera_move(C1, subj, (0, 0, -2000), (0, 0, -500), 1.0, ease="linear")
        self.advance(10.0)
        self.assertAlmostEqual(self.eye_of(C1).z, -500, places=0)

    def test_the_shot_stays_legal_the_whole_way(self):
        # dolly == target on every frame, or the engine draws black.
        subj = camera_anchor(0, 0, 0)
        camera_move(C1, subj, (0, 500, -3000), (0, 100, -400), 2.0)
        for _ in range(6):
            self.advance(0.4)
            state = mock_sbs._cinematic.get(C1)
            self.assertEqual(state["dolly_id"], state["target_id"])

    def test_it_follows_a_moving_subject(self):
        # The offset is recomputed from wherever the subject IS, so a move on a
        # travelling ship stays framed without a second driver.
        subj_id = camera_anchor(0, 0, 0)
        camera_move(C1, subj_id, (0, 0, -1000), (0, 0, -1000), 4.0)
        self.advance(1.0)
        before = mock_sbs._cinematic[C1]["dolly_off"]
        obj = mock_sbs.sim.get_space_object(subj_id)
        obj.pos.x += 5000
        self.advance(1.0)
        after = mock_sbs._cinematic[C1]["dolly_off"]
        self.assertNotAlmostEqual(before[0], after[0], places=0)
        self.assertAlmostEqual(self.eye_of(C1).x, 0, places=0)

    def test_a_second_move_replaces_the_first(self):
        # Two drivers re-aiming one console would fight tick by tick, and the
        # jitter reads as an engine bug rather than a second caller.
        subj = camera_anchor(0, 0, 0)
        camera_move(C1, subj, (0, 0, -4000), (0, 0, -3000), 10.0)
        camera_move(C1, subj, (0, 0, -1000), (0, 0, -900), 10.0)
        self.assertEqual(len([1 for cid in _MOVES if cid == C1]), 1)
        self.advance(0.2)
        self.assertLess(abs(self.eye_of(C1).z + 1000), 200)

    def test_moves_on_different_consoles_are_independent(self):
        subj = camera_anchor(0, 0, 0)
        camera_move(C1, subj, (0, 0, -4000), (0, 0, -4000), 5.0)
        camera_move(C2, subj, (0, 0, -800), (0, 0, -800), 5.0)
        self.advance(1.0)
        self.assertAlmostEqual(self.eye_of(C1).z, -4000, places=0)
        self.assertAlmostEqual(self.eye_of(C2).z, -800, places=0)

    def test_no_audience_resolves_rather_than_hanging(self):
        subj = camera_anchor(0, 0, 0)
        prom = camera_move([], subj, (0, 0, -1), (0, 0, -2), 1.0)
        self.assertTrue(prom.done(), "a shot nobody can see must not hang the story")


class TestOrbit(MoveBase):
    def test_it_holds_its_distance(self):
        subj_id = camera_anchor(0, 0, 0)
        camera_orbit(C1, subj_id, 2000, 0, 360, seconds=4.0, pitch=0.0)
        seen = []
        for _ in range(8):
            self.advance(0.5)
            eye = self.eye_of(C1)
            seen.append((eye.x ** 2 + eye.y ** 2 + eye.z ** 2) ** 0.5)
        for d in seen:
            self.assertAlmostEqual(d, 2000, delta=60)

    def test_it_actually_goes_round(self):
        subj_id = camera_anchor(0, 0, 0)
        camera_orbit(C1, subj_id, 2000, 0, 180, seconds=4.0, pitch=0.0)
        first = self.eye_of(C1)
        self.advance(4.5)
        last = self.eye_of(C1)
        moved = ((first.x - last.x) ** 2 + (first.z - last.z) ** 2) ** 0.5
        self.assertGreater(moved, 2000, "half an orbit should cross the subject")

    def test_it_orbits_a_moving_subject(self):
        subj_id = camera_anchor(0, 0, 0)
        camera_orbit(C1, subj_id, 1500, 0, 360, seconds=6.0, pitch=0.0)
        self.advance(1.0)
        obj = mock_sbs.sim.get_space_object(subj_id)
        obj.pos.x += 9000
        self.advance(1.0)
        eye = self.eye_of(C1)
        d = ((eye.x - 9000) ** 2 + eye.y ** 2 + eye.z ** 2) ** 0.5
        self.assertAlmostEqual(d, 1500, delta=60)


class TestRack(MoveBase):
    def test_it_re_aims_without_moving_the_lens(self):
        a = camera_anchor(0, 0, 0)
        b = camera_anchor(6000, 0, 0)
        camera_move(C1, a, (0, 300, -1500), (0, 300, -1500), 1.0)
        self.advance(0.1)
        before = self.eye_of(C1)
        camera_rack(C1, b)
        after = self.eye_of(C1)
        self.assertAlmostEqual(before.x, after.x, places=0)
        self.assertAlmostEqual(before.z, after.z, places=0)
        self.assertEqual(mock_sbs._cinematic[C1]["dolly_id"], b)

    def test_it_stops_a_running_move(self):
        # A rack during a move is a new intent, not a modifier on the old one.
        a = camera_anchor(0, 0, 0)
        b = camera_anchor(6000, 0, 0)
        camera_move(C1, a, (0, 0, -4000), (0, 0, -100), 10.0)
        self.advance(0.2)
        camera_rack(C1, b)
        held = self.eye_of(C1)
        self.advance(3.0)
        self.assertAlmostEqual(self.eye_of(C1).z, held.z, places=0,
                               msg="the old move was still driving")

    def test_with_nothing_recorded_it_declines(self):
        # The engine cannot be asked where the lens is, so without a recorded
        # position a rack would have to invent one.
        b = camera_anchor(6000, 0, 0)
        self.assertEqual(camera_rack(C1, b), 0)


class TestStopAndState(MoveBase):
    def test_stop_leaves_the_lens_where_it_is(self):
        subj = camera_anchor(0, 0, 0)
        camera_move(C1, subj, (0, 0, -4000), (0, 0, -100), 10.0)
        self.advance(1.0)
        where = self.eye_of(C1)
        camera_move_stop(C1)
        self.advance(3.0)
        self.assertAlmostEqual(self.eye_of(C1).z, where.z, places=0)

    def test_camera_eye_reports_the_lens(self):
        subj = camera_anchor(0, 0, 0)
        camera_move(C1, subj, (0, 0, -2500), (0, 0, -2500), 2.0)
        self.advance(0.2)
        self.assertAlmostEqual(camera_eye(C1).z, -2500, places=0)

    def test_a_finished_move_leaves_nothing_behind(self):
        # Registered in the reset ledger, so a leak here is reported by name -
        # and a driver that outlived its shot would re-aim the next one.
        subj = camera_anchor(0, 0, 0)
        camera_move(C1, subj, (0, 0, -2000), (0, 0, -500), 1.0)
        self.advance(3.0)
        self.assertEqual(len(_MOVES), 0)

    def test_a_live_move_is_reported_by_the_reset_audit(self):
        # The audit lists only NON-EMPTY containers, so the meaningful check is that
        # a running driver shows up by name - an unregistered container is invisible
        # to the restart soak, which is how brains stopped ticking after run 1.
        from sbs_utils.handlerhooks import reset_mission_audit, _RESET_PROBES
        self.assertIn("camera moves", _RESET_PROBES)
        self.assertNotIn("camera moves", reset_mission_audit())
        subj = camera_anchor(0, 0, 0)
        camera_move(C1, subj, (0, 0, -2000), (0, 0, -500), 10.0)
        self.assertEqual(reset_mission_audit().get("camera moves"), 1)


if __name__ == "__main__":
    unittest.main()
