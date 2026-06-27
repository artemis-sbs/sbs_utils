"""Tests for the a2x coordinate/heading conversion helpers."""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

from sbs_utils.vec import Vec3
from sbs_utils.procedural.a2x.coords import pos, angle, A2X_MAP_SIZE


class A2xCoordsTests(unittest.TestCase):
    def test_pos_mirrors_x_and_z_keeps_y(self):
        v = pos(98000, 7, 98000)
        self.assertIsInstance(v, Vec3)
        self.assertEqual((v.x, v.y, v.z), (2000, 7, 2000))

    def test_pos_matches_from2x_coord(self):
        for x, y, z in [(0, 0, 0), (50000, -200, 50000), (100000, 10, 1)]:
            a = pos(x, y, z)
            b = Vec3.from2x_coord(x, y, z)
            self.assertEqual((a.x, a.y, a.z), (b.x, b.y, b.z))

    def test_pos_centre_is_fixed_point(self):
        c = A2X_MAP_SIZE / 2
        v = pos(c, 0, c)
        self.assertEqual((v.x, v.z), (c, c))

    def test_pos_unpacks(self):
        x, y, z = pos(70000, 0, 40000)
        self.assertEqual((x, y, z), (30000, 0, 60000))

    def test_angle_adds_180_mod_360(self):
        self.assertEqual(angle(0), 180.0)
        self.assertEqual(angle(120), 300.0)
        self.assertEqual(angle(270), 90.0)
        self.assertEqual(angle(360), 180.0)

    def test_angle_stays_in_range(self):
        for d in range(0, 720, 15):
            self.assertTrue(0.0 <= angle(d) < 360.0)


if __name__ == "__main__":
    unittest.main()
