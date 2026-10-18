"""A rail leg's clearance is its TRUE pinch, not the best of nine samples.

The C4-08 ruin (a sphere room with a narrow passage out of it): the cheapest route to The
Altar cut the concave corner where the room meets the passage. Nine evenly spaced samples
straddled the pinch and read 43.7 where the true minimum is about 27.7, so the leg cost
little and won - and in the engine the suit's containment caught it at that corner six
re-plans running (course c4-08, 2026-10-17). Sampled at most every RAIL_CLEAR_SPACING,
the leg reads its pinch and the route meets the passage on its axis instead.

    python -m unittest tests.test_rails_leg_pinch
"""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

from sbs_utils.procedural import rails as RL
from sbs_utils.procedural import volume as V


class LegPinch(unittest.TestCase):
    def setUp(self):
        V.volume_clear()
        RL.rail_clear()
        V.volume_define("pinch", chambers={"nave": (3000, 0, 0, 1100),
                                           "vault": (3000, 0, 2800, 700)},
                        passages=[("nave", "vault", 150)])
        self.vol = RL._vol_resolve("pinch")

    def tearDown(self):
        V.volume_clear()
        RL.rail_clear()

    def test_a_corner_leg_reads_its_true_pinch(self):
        a, b = (2681.0, 0.0, 552.0), (3000.0, 0.0, 1400.0)
        dense = RL._rail_leg_clearance(self.vol, a, b, samples=200)
        self.assertLess(RL._rail_leg_clearance(self.vol, a, b), dense + 3.0)

    def test_the_route_meets_the_passage_on_its_axis(self):
        RL.rail_build("pinch")
        route = RL.rail_route("pinch", (2000.0, 0.0, 0.0), (3000.0, 0.0, 2800.0))
        self.assertTrue(route)
        into = [p for p in route if p[2] > 1100.0]            # past the room's edge
        self.assertTrue(into)
        before = route[route.index(into[0]) - 1] if route.index(into[0]) > 0 else None
        self.assertIsNotNone(before)
        self.assertAlmostEqual(before[0], 3000.0, delta=40.0,
                               msg=f"the leg into the passage comes in from the side: {before}")


if __name__ == "__main__":
    unittest.main()
