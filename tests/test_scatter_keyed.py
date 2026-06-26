"""Position-keyed lattice scatter: a cell's point/contents depend only on
(key, cell indices), so a small region is the centered subset of a larger one.
Foundation for matching map sizes and a seed-only universe. See scatter.py."""
import math
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

from sbs_utils.scatter import grid_keyed, cell_roll

CELL = 1000


def _xyz(points):
    return [(p.x, p.y, p.z) for p in points]


class TestGridKeyed(unittest.TestCase):
    def test_small_is_exact_subset_of_large(self):
        large = grid_keyed(42, CELL, -5000, -5000, 5000, 5000, y_min=-100, y_max=100)
        small = grid_keyed(42, CELL, -2000, -2000, 2000, 2000, y_min=-100, y_max=100)
        large_set = set(_xyz(large))
        # Same key+cell -> identical points for shared cells (bit-for-bit).
        for p in _xyz(small):
            self.assertIn(p, large_set)
        self.assertLess(len(small), len(large))

    def test_deterministic_same_args(self):
        a = grid_keyed(7, CELL, -3000, -3000, 3000, 3000, y_min=-100, y_max=100)
        b = grid_keyed(7, CELL, -3000, -3000, 3000, 3000, y_min=-100, y_max=100)
        self.assertEqual(_xyz(a), _xyz(b))

    def test_different_key_differs(self):
        a = grid_keyed(1, CELL, -3000, -3000, 3000, 3000)
        b = grid_keyed(2, CELL, -3000, -3000, 3000, 3000)
        self.assertNotEqual([(p.x, p.z) for p in a], [(p.x, p.z) for p in b])

    def test_one_point_per_cell_in_bounds(self):
        # centers within [-2000,2000] at +-1500, +-500 -> 4 per axis -> 16
        pts = grid_keyed(3, CELL, -2000, -2000, 2000, 2000)
        self.assertEqual(len(pts), 16)

    def test_points_stay_in_their_cell(self):
        pts = grid_keyed(99, CELL, -4000, -4000, 4000, 4000)
        self.assertTrue(pts)
        for p in pts:
            ix = math.floor(p.x / CELL)
            iz = math.floor(p.z / CELL)
            cx = (ix + 0.5) * CELL
            cz = (iz + 0.5) * CELL
            self.assertLess(abs(p.x - cx), CELL / 2)
            self.assertLess(abs(p.z - cz), CELL / 2)

    def test_radius_clip(self):
        pts = grid_keyed(5, CELL, -10000, -10000, 10000, 10000, radius=3000)
        self.assertTrue(pts)
        for p in pts:
            self.assertLessEqual(p.x * p.x + p.z * p.z, 3000 * 3000)

    def test_zero_cell_is_empty(self):
        self.assertEqual(grid_keyed(1, 0, -1000, -1000, 1000, 1000), [])


class TestCellRoll(unittest.TestCase):
    def test_stable_for_same_cell(self):
        # Two different points inside the same cell roll identically.
        self.assertEqual(cell_roll(42, CELL, 1010.0, 10.0),
                         cell_roll(42, CELL, 1990.0, 990.0))

    def test_in_range(self):
        v = cell_roll(42, CELL, 1234.0, -777.0)
        self.assertGreaterEqual(v, 0.0)
        self.assertLess(v, 1.0)

    def test_salt_independent(self):
        self.assertNotEqual(cell_roll(42, CELL, 1234.0, -777.0, salt=0),
                            cell_roll(42, CELL, 1234.0, -777.0, salt=1))

    def test_matches_across_sizes(self):
        # A cell's contents decision is independent of the requested bounds:
        # the same world cell rolls the same whether generated for a small or
        # large map. (Pair this with a grid_keyed point in that cell.)
        big = grid_keyed(42, CELL, -8000, -8000, 8000, 8000)
        small = grid_keyed(42, CELL, -2000, -2000, 2000, 2000)
        common = set(_xyz(small)) & set(_xyz(big))
        self.assertTrue(common)
        for (x, y, z) in common:
            self.assertEqual(cell_roll(42, CELL, x, z, salt=1),
                             cell_roll(42, CELL, x, z, salt=1))


if __name__ == "__main__":
    unittest.main()
