"""The establishing two-shot: a ship framed WITH the world it is orbiting.

The shot everyone pictures when they say "in orbit" - hull in frame, planet behind it
or off one edge. `camera_orbit` cannot make it: it swings the lens around ONE object,
so aimed at the planet there is no ship in shot, and aimed at the ship the planet lands
wherever the ship's heading happens to put it.

What makes this shot is that the lens sits in the frame the TWO bodies define, so these
tests assert the GEOMETRY - where the world falls relative to the lens and the ship -
rather than that some function got called. A shot that "runs" and puts the planet
off-camera is the exact failure this is for.

    python -m unittest tests.test_camera_establishing
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import math
import unittest

from cosmos_dev.mock import sbs as mock_sbs
from sbs_utils.helpers import FrameContext, Context, FakeEvent
from sbs_utils.spaceobject import SpaceObject
from sbs_utils.objects import Npc, PlayerShip
from sbs_utils.procedural.query import to_object
from sbs_utils.tickdispatcher import TickDispatcher
from sbs_utils.delete_queue import DeleteQueue
from sbs_utils.vec import Vec3
from sbs_utils.procedural.gui.camera import (
    ESTABLISHING_ANGLES, ESTABLISHING_MAX_CONE, camera_establishing,
    camera_move_stop, _MOVES)

C1 = 0x8000000000000001


def _unit(v):
    n = v.length() or 1.0
    return Vec3(v.x / n, v.y / n, v.z / n)


class EstablishingBase(unittest.TestCase):
    def setUp(self):
        mock_sbs.create_new_sim()
        SpaceObject.clear()
        TickDispatcher.clear()
        mock_sbs._cinematic.clear()
        _MOVES.clear()
        FrameContext.context = Context(mock_sbs.sim, mock_sbs, FakeEvent())
        # A world at the origin and a ship out along +Z, which makes the radial axis
        # +Z and the tangent axis +X - so every assertion below can be read by eye.
        # to_object: spawn() hands back SpawnData, and a `.pos` write on THAT moves
        # nothing - the shot then never followed and the failure read as a broken camera.
        self.world = to_object(Npc().spawn(0, 0, 0, "Kaleth", "tsn", "Starbase", "behav_station"))
        self.ship = to_object(PlayerShip().spawn(0, 0, 12000, "Artemis", "tsn", "Battle Cruiser"))
        # A WORLDLET, not a starbase. The size is the point: a body fills frame because
        # it subtends a wide angle, not because its centre sits near the view axis, and a
        # test that framed a 200m station would demand a composition no orbital shot has
        # ever used. This is prefab_gas_giant's own geometry - planet_radius 4000, and
        # the exclusion radius twice that, which is the convention every planet follows.
        self.world.space_object().exclusion_radius = 8000.0

    def tearDown(self):
        TickDispatcher.clear()
        _MOVES.clear()
        DeleteQueue.clear()
        FrameContext.context = None

    def advance(self, seconds):
        from cosmos_dev.mock.sbs import TICKS_PER_SECOND
        for _ in range(int(seconds * TICKS_PER_SECOND) + 1):
            TickDispatcher.dispatch_tick()
            mock_sbs.sim._time_tick_counter += 1

    def lens_of(self, cid=C1):
        """WHERE THE ENGINE PUTS THE LENS, which is not where the offset points.

        The engine places the camera on the FAR side of the offset it is handed -
        mirrored through the dolly. Engine-observed: with the geometry logged and
        correct, the shot came out on the world side of the ship looking away from it,
        and the orbit tether ran from the hull toward the camera.

        It is invisible for every other shot in the library, because they all frame ONE
        object and a lens mirrored through its subject still frames that subject from
        the opposite side. So the mock's own reading - dolly + offset - is the kinder
        one, and a test using it blesses a shot that points the wrong way on real
        hardware. Model the engine.
        """
        state = mock_sbs._cinematic.get(cid)
        if state is None:
            return None
        obj = mock_sbs.sim.get_space_object(state["dolly_id"])
        off = state["dolly_off"]
        return Vec3(obj.pos.x - off[0], obj.pos.y - off[1], obj.pos.z - off[2])

    def run_angle(self, angle, seconds=4.0):
        camera_establishing(C1, self.ship, self.world, angle=angle, seconds=seconds,
                            arc=0)
        self.advance(seconds * 0.5)
        return self.lens_of()

    # What the shot is FOR: are BOTH bodies in the picture?
    def world_off_axis(self, lens):
        """Degrees between where the lens is aimed and the world's CENTRE.

        THE CENTRE, not the limb. The first cut of this test asked only whether some
        edge of the body clipped a 45 degree cone, which a huge planet satisfies while
        its centre sits 70 degrees off the view axis - off screen on any real lens. It
        passed, and Doug's answer to the shipped result was "you see the ship, not the
        worldlets". Ask the strict question.
        """
        view = _unit(Vec3(self.ship.pos.x - lens.x,
                          self.ship.pos.y - lens.y,
                          self.ship.pos.z - lens.z))
        to_world = _unit(Vec3(self.world.pos.x - lens.x,
                              self.world.pos.y - lens.y,
                              self.world.pos.z - lens.z))
        dot = max(-1.0, min(1.0, view.dot(to_world)))
        return math.degrees(math.acos(dot))

    # ON SCREEN is an absolute number, not whatever the constant happens to say.
    # Deliberately NOT ESTABLISHING_MAX_CONE: a test that reads the same constant the
    # code does cannot fail when that constant is wrong, and the cone is not even the
    # right quantity - it bounds where the lens SITS around the world, while what has
    # to fit in frame is the angle between the hull and the world as seen FROM there.
    # Sitting further out opens that gap wider than the cone.
    ON_SCREEN = 45.0

    def both_in_frame(self, lens):
        """The ship is the target so it is framed by construction; this is the world."""
        return self.world_off_axis(lens) <= self.ON_SCREEN


class TestTheShotIsAimedAtTheShip(EstablishingBase):

    def test_the_lens_rides_the_ship_not_the_world(self):
        # The difference from `orbit`. The engine's dolly and target are one object,
        # so whichever object that is decides what stays framed.
        camera_establishing(C1, self.ship, self.world, seconds=4.0)
        self.advance(1.0)
        state = mock_sbs._cinematic.get(C1)
        self.assertIsNotNone(state, "no shot was started")
        self.assertEqual(state["dolly_id"], self.ship.id)

    def test_it_follows_the_ship_around_its_orbit(self):
        # The frame is recomputed from live positions, so a ship that has travelled a
        # quarter of the way round is still framed the same way against the world.
        camera_establishing(C1, self.ship, self.world, angle="behind", seconds=20.0,
                            arc=0)
        self.advance(1.0)
        first = self.lens_of()
        self.ship.pos = Vec3(6000, 0, 0)      # a quarter turn
        self.advance(1.0)
        second = self.lens_of()
        self.assertGreater((Vec3(second.x - first.x, second.y - first.y,
                                 second.z - first.z)).length(), 1000,
                           "the lens did not move with the ship")
        self.assertTrue(self.both_in_frame(second),
                        "the world fell out of frame once the ship moved")


class TestTheWorldLandsWhereTheAngleSays(EstablishingBase):

    def test_every_angle_is_outside_the_orbit(self):
        # The cone is about the WORLD-WARD axis, so every angle looks inward past the
        # hull at the body beyond. A lens inside the orbit would have the world behind
        # the camera.
        for angle in ESTABLISHING_ANGLES:
            camera_move_stop(C1)
            lens = self.run_angle(angle)
            self.assertGreater(lens.length(), self.ship.pos.length(),
                               f"'{angle}' put the lens INSIDE the orbit")

    def test_side_leans_along_the_track(self):
        # roll 0 leans toward the tangent, which is X for a ship on +Z about the origin.
        lens = self.run_angle("side")
        self.assertGreater(abs(lens.x), 100, "the side angle did not lean along the track")
        self.assertTrue(self.both_in_frame(lens))

    def test_high_looks_down_across_the_ship(self):
        lens = self.run_angle("high")
        self.assertGreater(lens.y, 0, "a high angle must be above the orbital plane")
        self.assertTrue(self.both_in_frame(lens))

    def test_low_looks_up_past_the_hull(self):
        lens = self.run_angle("low")
        self.assertLess(lens.y, 0, "a low angle must be below the orbital plane")
        self.assertTrue(self.both_in_frame(lens))

    def test_no_named_angle_aims_away_from_the_world(self):
        for angle in ESTABLISHING_ANGLES:
            camera_move_stop(C1)
            off = self.world_off_axis(self.run_angle(angle))
            self.assertLessEqual(off, self.ON_SCREEN,
                                 f"'{angle}' aims {off:.0f} deg off the world")

    def test_an_over_wide_angle_is_clamped_rather_than_obeyed(self):
        # A composition wider than the cone puts the body off screen whatever its size,
        # so the request is honored as far as it can be and no further.
        off = self.world_off_axis(self.run_angle((85.0, 0.0)))
        self.assertLessEqual(off, self.ON_SCREEN,
                             f"an 85 degree request produced a {off:.0f} degree shot")

    def test_every_named_angle_keeps_the_world_on_screen(self):
        # The one property that makes any of these an establishing shot at all.
        for angle in ESTABLISHING_ANGLES:
            camera_move_stop(C1)
            lens = self.run_angle(angle)
            self.assertIsNotNone(lens, f"{angle} started no shot")
            self.assertTrue(self.both_in_frame(lens),
                            f"'{angle}' put the world off camera")

    def test_the_angles_are_actually_different_compositions(self):
        # Five names that framed the same picture would be a cut to nowhere.
        seen = []
        for angle in ESTABLISHING_ANGLES:
            camera_move_stop(C1)
            seen.append(self.run_angle(angle))
        for i in range(len(seen)):
            for j in range(i + 1, len(seen)):
                d = Vec3(seen[i].x - seen[j].x, seen[i].y - seen[j].y,
                         seen[i].z - seen[j].z).length()
                self.assertGreater(d, 200, "two angles frame the same shot")


class TestItDegradesRatherThanBreaking(EstablishingBase):

    def test_no_world_still_gives_a_watchable_shot(self):
        # Falls back to a plain back-and-above angle rather than framing the origin.
        camera_establishing(C1, self.ship, None, seconds=4.0)
        self.advance(1.0)
        lens = self.lens_of()
        self.assertIsNotNone(lens)
        near = Vec3(lens.x - self.ship.pos.x, lens.y - self.ship.pos.y,
                    lens.z - self.ship.pos.z).length()
        self.assertGreater(near, 1.0, "the lens collapsed onto the ship")

    def test_a_ship_at_the_world_centre_does_not_divide_by_zero(self):
        self.ship.pos = Vec3(0, 0, 0)
        camera_establishing(C1, self.ship, self.world, seconds=4.0)
        self.advance(1.0)
        self.assertIsNotNone(self.lens_of())

    def test_directly_over_the_pole_does_not_collapse(self):
        # The tangent is a cross product with world up; straight over the pole that
        # collapses to zero length and every later normalize would divide by it.
        self.ship.pos = Vec3(0, 6000, 0)
        camera_establishing(C1, self.ship, self.world, angle="side", seconds=4.0)
        self.advance(1.0)
        lens = self.lens_of()
        self.assertIsNotNone(lens)
        self.assertTrue(self.both_in_frame(lens))

    def test_an_unknown_angle_name_falls_back(self):
        camera_establishing(C1, self.ship, self.world, angle="sideways-ish",
                            seconds=4.0)
        self.advance(1.0)
        self.assertIsNotNone(self.lens_of())


if __name__ == "__main__":
    unittest.main()
