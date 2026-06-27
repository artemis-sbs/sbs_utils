"""Tests for a2x terrain point-planning (pure logic; no sbs runtime needed).

The public create_* spawners are thin pass-throughs to already-tested terrain
spawners; what matters to migration fidelity is the placement logic, tested here.
"""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

from sbs_utils.procedural.a2x.terrain import (
    _plan_points, _with_seed, _to_cosmos, _NEB_TYPE_COLOR,
)


class A2xTerrainPlanTests(unittest.TestCase):
    def test_point_mode_all_at_start(self):
        pts = _plan_points(5, (1000, 2, 3000))
        self.assertEqual(len(pts), 5)
        for p in pts:
            self.assertEqual((p.x, p.y, p.z), (1000, 2, 3000))

    def test_line_mode_count_and_endpoints(self):
        pts = _plan_points(4, (0, 0, 0), end=(300, 0, 0))
        self.assertEqual(len(pts), 4)
        # evenly spaced from start to end along x
        self.assertEqual(pts[0].x, 0)
        self.assertEqual(pts[-1].x, 300)

    def test_sphere_mode_count_and_radius(self):
        center = (0, 0, 0)
        pts = _plan_points(20, center, radius=5000)
        self.assertEqual(len(pts), 20)
        for p in pts:
            d = (p.x ** 2 + p.y ** 2 + p.z ** 2) ** 0.5
            self.assertLessEqual(d, 5000 + 1e-6)

    def test_zero_count(self):
        self.assertEqual(_plan_points(0, (0, 0, 0)), [])

    def test_jitter_within_bounds(self):
        rr = 250
        pts = _plan_points(50, (0, 0, 0), random_range=rr)
        for p in pts:
            self.assertLessEqual(abs(p.x), rr)
            self.assertLessEqual(abs(p.y), rr)
            self.assertLessEqual(abs(p.z), rr)

    def test_end_takes_precedence_over_radius(self):
        # When both end and radius are given, line mode wins (deterministic x spread).
        pts = _plan_points(3, (0, 0, 0), end=(200, 0, 0), radius=9999)
        self.assertEqual([p.x for p in pts], [0, 100, 200])

    def test_seed_reproducible(self):
        def plan():
            return _plan_points(30, (0, 0, 0), radius=4000, random_range=300)
        a = _with_seed(123, plan)
        b = _with_seed(123, plan)
        self.assertEqual([(p.x, p.y, p.z) for p in a],
                         [(p.x, p.y, p.z) for p in b])

    def test_seed_restores_global_rng(self):
        import random
        random.seed(7)
        before = random.random()
        random.seed(7)
        _with_seed(999, lambda: _plan_points(10, (0, 0, 0), radius=100, random_range=10))
        after = random.random()
        # global stream undisturbed by the seeded block
        self.assertEqual(before, after)

    def test_to_cosmos_mirrors(self):
        cs, ce = _to_cosmos((98000, 7, 98000), (0, 0, 0))
        self.assertEqual(cs, (2000, 7, 2000))
        self.assertEqual(ce, (100000, 0, 100000))

    def test_to_cosmos_no_end(self):
        cs, ce = _to_cosmos((50000, 0, 50000), None)
        self.assertEqual(cs, (50000, 0, 50000))
        self.assertIsNone(ce)

    def test_nebtype_color_map(self):
        self.assertEqual(_NEB_TYPE_COLOR[1], "red")
        self.assertEqual(set(_NEB_TYPE_COLOR), {1, 2, 3})


if __name__ == "__main__":
    unittest.main()
