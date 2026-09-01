"""Which side of the offset the engine puts the lens on, and who that breaks.

THE FINDING (engine-observed 2026-08-31). The engine places the camera on the FAR side
of the offset it is handed - mirrored through the dolly. Hand it ``+Z * 500`` and the
lens ends up 500 units along ``-Z``.

WHY IT SURVIVED THIS LONG. It is invisible to a single-subject shot: a lens mirrored
through its subject still frames that subject, just from a side nobody asked for. Every
move in this module framed one object, so nobody could see it. `camera_orbit_lens` even
documents ``Vec3(0, 0, distance)`` as "straight back" - true only once mirrored, which
says the offsets here were authored against the behavior rather than the arithmetic.

WHO IT BREAKS. The shots that compute a real world position from real geometry:

* `camera_chase`, whose whole promise is to sit BEHIND a heading - it sat in front,
  and had **no test of its own at all**, which is how it shipped that way.
* `camera_establishing`, which must be opposite a second body.

WHO IT DOES NOT BREAK. `camera_dolly` and `camera_orbit` build their offset in the
engine's own convention (`camera_orbit_lens`) and are correct as they stand. This test
pins that too, so a well-meaning fix at the wrong layer fails here rather than silently
re-framing every authored cutscene.

    python -m unittest tests.test_camera_convention
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest

from cosmos_dev.mock import sbs as mock_sbs
from sbs_utils.helpers import FrameContext, Context, FakeEvent
from sbs_utils.spaceobject import SpaceObject
from sbs_utils.objects import PlayerShip
from sbs_utils.procedural.query import to_object
from sbs_utils.tickdispatcher import TickDispatcher
from sbs_utils.delete_queue import DeleteQueue
from sbs_utils.vec import Vec3
from sbs_utils.procedural.gui.camera import (
    camera_chase, camera_dolly, camera_orbit_lens, camera_shot, camera_move_stop, _MOVES)

C1 = 0x8000000000000001


class ConventionBase(unittest.TestCase):
    def setUp(self):
        mock_sbs.create_new_sim()
        SpaceObject.clear()
        TickDispatcher.clear()
        mock_sbs._cinematic.clear()
        _MOVES.clear()
        FrameContext.context = Context(mock_sbs.sim, mock_sbs, FakeEvent())
        self.ship = to_object(PlayerShip().spawn(0, 0, 0, "Artemis", "tsn", "Battle Cruiser"))

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

    def offset(self, cid=C1):
        """Exactly what was handed to the engine."""
        state = mock_sbs._cinematic.get(cid)
        return None if state is None else state["dolly_off"]

    def engine_lens(self, cid=C1):
        """Where the ENGINE puts the lens: the dolly MINUS the offset."""
        state = mock_sbs._cinematic.get(cid)
        if state is None:
            return None
        obj = mock_sbs.sim.get_space_object(state["dolly_id"])
        off = state["dolly_off"]
        return Vec3(obj.pos.x - off[0], obj.pos.y - off[1], obj.pos.z - off[2])


class TestTheConvention(ConventionBase):

    def test_camera_shot_hands_over_the_offset_toward_the_wanted_point(self):
        # Documenting what camera_shot DOES, so the mirror is visible in one place.
        camera_shot(C1, self.ship, Vec3(0, 0, 900))
        off = self.offset()
        self.assertAlmostEqual(off[2], 900.0, places=3)
        # ...and therefore the engine renders it at -900. This is the whole finding.
        self.assertAlmostEqual(self.engine_lens().z, -900.0, places=3)


class TestChaseSitsBehind(ConventionBase):
    """`camera_chase` had NO test. That is why it shipped pointing the wrong way."""

    def _face(self, x, y, z):
        # The mock derives forward_vector from the object's heading.
        eo = self.ship.space_object()
        eo.side_vector, eo.up_vector = None, None
        self.ship.pos = Vec3(0, 0, 0)
        eo.host_id = 0
        import math
        eo.pitch, eo.roll = 0.0, 0.0
        eo.heading = math.degrees(math.atan2(x, z))
        return eo.forward_vector()

    def test_the_lens_is_behind_the_subject(self):
        fwd = self._face(0, 0, 1)          # pointing along +Z
        camera_chase(C1, self.ship, 800, height=50, seconds=4.0)
        self.advance(1.0)
        lens = self.engine_lens()
        self.assertIsNotNone(lens, "no chase shot started")
        # Behind means OPPOSITE the forward vector.
        along = lens.x * fwd.x + lens.y * fwd.y + lens.z * fwd.z
        self.assertLess(along, 0,
                        "the chase camera is IN FRONT of what it is chasing")

    def test_it_is_roughly_the_distance_asked_for(self):
        self._face(0, 0, 1)
        camera_chase(C1, self.ship, 800, height=0, seconds=4.0)
        self.advance(1.0)
        self.assertAlmostEqual(self.engine_lens().length(), 800.0, delta=60.0)

    def test_the_no_heading_fallback_is_also_behind(self):
        # A rock, or an engine object that will not answer. Still must not sit in front.
        eo = self.ship.space_object()
        eo.forward_vector = lambda: (_ for _ in ()).throw(RuntimeError("no heading"))
        camera_chase(C1, self.ship, 700, height=0, seconds=4.0)
        self.advance(1.0)
        lens = self.engine_lens()
        self.assertIsNotNone(lens)
        self.assertAlmostEqual(lens.z, -700.0, delta=1.0)


class TestTheAngleShotsAreLeftAlone(ConventionBase):
    """`camera_dolly` / `camera_orbit` are authored in the engine's own convention.

    Fixing the mirror at the wrong layer - inside `camera_shot`, say - would silently
    re-frame every cutscene in every repo. These pin that it did not happen.
    """

    def test_a_dolly_hands_over_camera_orbit_lens_unchanged(self):
        camera_dolly(C1, self.ship, 1000, 1000, yaw=0.0, pitch=0.0, seconds=4.0)
        self.advance(0.5)
        off = self.offset()
        want = camera_orbit_lens(1000, 0.0, 0.0)
        for got, expect, axis in zip(off, (want.x, want.y, want.z), "xyz"):
            self.assertAlmostEqual(got, expect, delta=1.0,
                                   msg=f"dolly offset changed on {axis}")


if __name__ == "__main__":
    unittest.main()
