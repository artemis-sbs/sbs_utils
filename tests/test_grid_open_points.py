"""get_open_grid_points walks the WHOLE hull map, not a w x w square of it.

It looped `y` over `hull_map.w`, so on a hull taller than it is wide (every Venus hull:
14x24) the rows past the width - the stern, where the engines are - never came back as
open, and on a wide hull it read past the last row.
"""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

from cosmos_dev.mock import sbs
from sbs_utils.helpers import FrameContext, Context, FakeEvent
from sbs_utils.procedural.grid import get_open_grid_points


class _HullMap:
    """A w x h hull map with every cell open, and a record of what was asked."""

    def __init__(self, w, h):
        self.w, self.h = w, h
        self.asked = []

    def is_grid_point_open(self, x, y):
        self.asked.append((x, y))
        return 1 if 0 <= x < self.w and 0 <= y < self.h else 0


class TestOpenGridPoints(unittest.TestCase):
    def setUp(self):
        sbs.create_new_sim()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent())
        self._real = sbs.get_hull_map

    def tearDown(self):
        sbs.get_hull_map = self._real

    def _open(self, w, h):
        hm = _HullMap(w, h)
        sbs.get_hull_map = lambda _id, *a, **k: hm
        return get_open_grid_points(1), hm

    def test_a_tall_hull_returns_every_row(self):
        points, _hm = self._open(3, 7)
        self.assertEqual(len(points), 21)
        self.assertEqual(max(int(p.y) for p in points), 6)

    def test_a_wide_hull_never_reads_past_its_last_row(self):
        points, hm = self._open(7, 3)
        self.assertEqual(len(points), 21)
        self.assertTrue(all(y < 3 for _x, y in hm.asked))


if __name__ == "__main__":
    unittest.main()
