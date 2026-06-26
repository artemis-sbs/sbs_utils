"""Position-keyed terrain field planner: decides nebula/asteroid per lattice
cell from (key, position) only, so a small map's field is the centered subset of
a larger one. Pure logic (no spawning). See terrain.terrain_field_plan_keyed."""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

from sbs_utils.procedural.terrain import terrain_field_plan_keyed
from sbs_utils.vec import Vec3

CELL = 1000


def _entries(plan):
    return [(round(p.x, 6), round(p.z, 6), kind) for (p, kind) in plan]


class TestTerrainFieldPlanKeyed(unittest.TestCase):
    def test_deterministic(self):
        a = terrain_field_plan_keyed(42, CELL, -5000, -5000, 5000, 5000, 0.3, 0.3)
        b = terrain_field_plan_keyed(42, CELL, -5000, -5000, 5000, 5000, 0.3, 0.3)
        self.assertEqual(_entries(a), _entries(b))

    def test_small_is_subset_of_large(self):
        large = terrain_field_plan_keyed(42, CELL, -8000, -8000, 8000, 8000, 0.3, 0.3)
        small = terrain_field_plan_keyed(42, CELL, -3000, -3000, 3000, 3000, 0.3, 0.3)
        large_set = set(_entries(large))
        self.assertTrue(_entries(small))
        for e in _entries(small):
            self.assertIn(e, large_set)
        self.assertLess(len(small), len(large))

    def test_chances_split(self):
        all_neb = terrain_field_plan_keyed(7, CELL, -3000, -3000, 3000, 3000, 1.0, 0.0)
        all_ast = terrain_field_plan_keyed(7, CELL, -3000, -3000, 3000, 3000, 0.0, 1.0)
        self.assertTrue(all(k == "nebula" for _, k in all_neb))
        self.assertTrue(all(k == "asteroid" for _, k in all_ast))
        # full coverage selects every cell
        self.assertEqual(len(all_neb), len(all_ast))

    def test_zero_chance_empty(self):
        self.assertEqual(terrain_field_plan_keyed(7, CELL, -3000, -3000, 3000, 3000, 0.0, 0.0), [])

    def test_exclude_clears_area(self):
        full = terrain_field_plan_keyed(5, CELL, -5000, -5000, 5000, 5000, 1.0, 0.0)
        excl = terrain_field_plan_keyed(5, CELL, -5000, -5000, 5000, 5000, 1.0, 0.0,
                                        exclude=[Vec3(0, 0, 0)], exclude_radius=3000)
        self.assertLess(len(excl), len(full))
        # nothing within the cleared radius remains
        for p, _ in excl:
            self.assertGreater(p.x * p.x + p.z * p.z, 0)  # at least not exactly origin
        near = [(p.x, p.z) for p, _ in excl if (p.x * p.x + p.z * p.z) < 3000 * 3000]
        self.assertEqual(near, [])


if __name__ == "__main__":
    unittest.main()
