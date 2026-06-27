"""Tests for a2x condition helpers (is_docked, in_box)."""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import cosmos_dev.mock.sbs as sbs
from tests.reset_helper import reset_mock
from sbs_utils.procedural.a2x.conditions import is_docked, in_box
from sbs_utils.procedural.a2x.spawn import create_enemy
from sbs_utils.procedural.query import to_id


class A2xConditionsTests(unittest.TestCase):
    def setUp(self):
        self.sim = reset_mock(sbs)

    def test_is_docked_default_undocked(self):
        so = create_enemy(0, 0, 0, "kralien_cruiser", name="X")
        # fresh object: no dock_state or "undocked" -> not docked
        self.assertFalse(is_docked(so))

    def test_is_docked_true_when_state_set(self):
        so = create_enemy(0, 0, 0, "kralien_cruiser", name="X")
        to_object_data = sbs  # noqa: keep import side
        obj = __import__("sbs_utils.procedural.query", fromlist=["to_object"]).to_object(so)
        obj.data_set.set("dock_state", "DS38")
        self.assertTrue(is_docked(so))

    def test_in_box_flips_corners(self):
        # 2.8 box x in [60000,80000], z in [20000,30000]; an object at 2.8 (70000,*,25000)
        # is inside. After the flip both the object and the corners move together.
        so = create_enemy(70000, 0, 25000, "kralien_cruiser", name="X")
        self.assertTrue(in_box(so, 60000, 20000, 80000, 30000))
        self.assertFalse(in_box(so, 0, 0, 1000, 1000))

    def test_in_box_outside_semantics(self):
        so = create_enemy(70000, 0, 25000, "kralien_cruiser", name="X")
        self.assertFalse(in_box(so, 60000, 20000, 80000, 30000, inside=False))


if __name__ == "__main__":
    unittest.main()
