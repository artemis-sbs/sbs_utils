"""amd_chain (compose parse-fact handlers) + amd_mission_data (quest+scan+landmark), which
let a mission author all its content sections in ONE .amd.

Run: python -m unittest tests.test_amd_mission
"""
import unittest
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import sbs_utils.mast_sbs.story_nodes  # import first to break a circular import
from sbs_utils.procedural.amd import amd_parse_facts, amd_chain
from sbs_utils.procedural.amd_mission import amd_mission_data


class AmdChainTests(unittest.TestCase):
    def test_first_handler_that_claims_wins(self):
        def h_a(d, l, v):
            if l == "a":
                d["A"] = v
                return True
        def h_b(d, l, v):
            if l == "b":
                d["B"] = v
                return True
        d = amd_parse_facts("a: 1\nb: 2\nc: 3", amd_chain(h_a, h_b))
        self.assertEqual(d["A"], "1")
        self.assertEqual(d["B"], "2")
        self.assertEqual(d["c"], 3)          # unclaimed -> default coercion

    def test_none_handlers_skipped(self):
        d = amd_parse_facts("x: 5", amd_chain(None, None))
        self.assertEqual(d["x"], 5)


class AmdMissionDataTests(unittest.TestCase):
    def test_quest_fence(self):
        d = amd_mission_data("State: active\nGoal: destroy 3 raiders\nPays: 100 credits")
        self.assertEqual(d["on_kill"], {"role": "raider", "count": 3})
        self.assertEqual(d["reward"], {"credits": 100})

    def test_scan_fence_b_form(self):
        d = amd_mission_data("Scan of: wreck\nTab: mat")
        self.assertEqual(d.get("scan_of"), "wreck")
        self.assertEqual(d.get("tab"), "mat")

    def test_landmark_fence_loc_is_list(self):
        d = amd_mission_data("Kind: station\nArt: base\nLoc: 100, 0, -50")
        self.assertEqual(d["kind"], "station")
        self.assertEqual(d["loc"], [100.0, 0.0, -50.0])   # landmark handler parsed the coords


if __name__ == "__main__":
    unittest.main()
