"""Persisted per-pair diplomacy overrides (sbs_utils.procedural.sides), promoted from OU.

The key/set are pure dict ops (unit-testable); apply drives side_set_relations. Run:
    python -m unittest tests.test_side_diplomacy
"""
import unittest
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import sbs_utils.mast_sbs.story_nodes  # noqa: F401
from sbs_utils.procedural.sides import side_diplomacy_key, side_diplomacy_set


class SideDiplomacyTests(unittest.TestCase):
    def test_key_is_order_independent(self):
        self.assertEqual(side_diplomacy_key("tsn", "raider"),
                         side_diplomacy_key("raider", "tsn"))

    def test_set_creates_and_records(self):
        d = side_diplomacy_set(None, "tsn", "raider", 2)
        self.assertEqual(d, {side_diplomacy_key("tsn", "raider"): 2})

    def test_set_symmetric_overwrites_same_key(self):
        d = side_diplomacy_set(None, "tsn", "raider", 2)
        d = side_diplomacy_set(d, "raider", "tsn", 0)   # same pair, reversed
        self.assertEqual(len(d), 1)
        self.assertEqual(d[side_diplomacy_key("tsn", "raider")], 0)

    def test_set_coerces_to_int(self):
        d = side_diplomacy_set(None, "a", "b", 3.0)
        self.assertEqual(d[side_diplomacy_key("a", "b")], 3)
        self.assertIsInstance(d[side_diplomacy_key("a", "b")], int)


if __name__ == "__main__":
    unittest.main()
