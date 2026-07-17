"""Tests for the AMD science-scan vocabulary (sbs_utils.procedural.amd_science).

Authors define per-role scans declaratively in an .amd file with the dialogue-native form:
one heading per (role, tab), bound by `Scan of:` (+ optional `Tab:`), the body's `%` lines
its random variants. science_define_scan_amd registers a whole doc. (The flat `Scan: <text>`
fence form was retired - this single form is the only one.)

Run: python -m unittest tests.test_amd_science
"""
import unittest
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import sbs_utils.mast_sbs.story_nodes  # import first to break a circular import
from cosmos_dev.mock import sbs
from sbs_utils.helpers import FrameContext, Context
from sbs_utils.spaceobject import SpaceObject
from sbs_utils.procedural.spawn import npc_spawn
from sbs_utils.procedural.query import to_id
from sbs_utils.procedural.science import science_clear_scan_defs, science_scan_tab, science_has_scan_def
from sbs_utils.procedural.amd_science import amd_scan_data, science_define_scan_amd


class FakeEvent:
    client_id = 0
    tag = ""
    sub_tag = ""
    origin_id = 0
    selected_id = 0
    parent_id = 0
    value_tag = ""
    extra_tag = ""
    extra_extra_tag = ""
    sub_float = 0.0
    source_point = None
    event_time = 0


class AmdScanDataTests(unittest.TestCase):
    def test_scan_of_and_tab_coerce(self):
        # the scan fence carries only Scan of: / Tab: (the text is in the body); default
        # coercion lowercases + underscores the labels
        d = amd_scan_data("Scan of: wreck\nTab: mat")
        self.assertEqual(d.get("scan_of"), "wreck")
        self.assertEqual(d.get("tab"), "mat")


class ScienceDefineScanAmdTests(unittest.TestCase):
    def setUp(self):
        sbs.create_new_sim()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent())
        SpaceObject.clear()
        science_clear_scan_defs()
        self.rock = to_id(npc_spawn(0, 0, 0, "Rock", "hazard_rock", "tsn_light_cruiser", "behav_npcship"))
        self.poacher = to_id(npc_spawn(0, 0, 100, "Trawler", "poacher", "tsn_light_cruiser", "behav_npcship"))

    def _doc(self):
        # mimic document_get_amd_file's parsed shape: children with key/description/data.
        # One heading per (role, tab); Scan of: binds the role, the body holds the text.
        return {"children": [
            {"key": "rock_scan", "data": {"scan of": "hazard_rock", "tab": "scan"},
             "description": "A dense asteroid."},
            {"key": "rock_mat", "data": {"scan of": "hazard_rock", "tab": "mat"},
             "description": "High iron."},
            {"key": "poach_intel", "data": {"scan of": "poacher", "tab": "intel"},
             "description": "Board, don't destroy."},
        ]}

    def test_registers_each_role(self):
        science_define_scan_amd(self._doc())
        self.assertTrue(science_has_scan_def(self.rock))
        self.assertEqual(science_scan_tab(self.rock, "scan"), "A dense asteroid.")
        self.assertEqual(science_scan_tab(self.rock, "mat"), "High iron.")
        self.assertEqual(science_scan_tab(self.poacher, "intel"), "Board, don't destroy.")

    def test_tab_defaults_to_scan(self):
        # a Scan of: heading with no Tab: registers the body under the scan tab
        doc = {"children": [
            {"key": "rock_default", "data": {"scan of": "hazard_rock"},
             "description": "A drifting hulk."},
        ]}
        science_define_scan_amd(doc)
        self.assertEqual(science_scan_tab(self.rock, "scan"), "A drifting hulk.")

    def test_dialogue_native_random_variants(self):
        # Option B: one heading per (role, tab); Scan of: binds it; body % lines are variants.
        doc = {"children": [
            {"key": "rock_hull", "data": {"scan of": "hazard_rock", "tab": "scan"},
             "description": "% Dense metallic asteroid.\n% A tumbling nickel-iron boulder."},
            {"key": "rock_mat", "data": {"scan of": "hazard_rock", "tab": "mat"},
             "description": "High nickel-iron content."},
        ]}
        science_define_scan_amd(doc)
        for _ in range(10):
            self.assertIn(science_scan_tab(self.rock, "scan"),
                          ["Dense metallic asteroid.", "A tumbling nickel-iron boulder."])
        self.assertEqual(science_scan_tab(self.rock, "mat"), "High nickel-iron content.")

    def test_dialogue_native_body_placeholder(self):
        # {captain} in a BODY line is safe (never hits YAML flow) and interpolates
        doc = {"children": [
            {"key": "poach_intel", "data": {"scan of": "poacher", "tab": "intel"},
             "description": "Registered to Captain {captain}."},
        ]}
        science_define_scan_amd(doc)
        from sbs_utils.procedural.inventory import set_inventory_value
        set_inventory_value(self.poacher, "captain", "Marlin")
        self.assertEqual(science_scan_tab(self.poacher, "intel"), "Registered to Captain Marlin.")

    def test_headings_for_same_role_compose(self):
        # multiple Scan of: headings for one role merge their tabs
        doc = {"children": [
            {"key": "rock_mat", "data": {"scan of": "hazard_rock", "tab": "mat"},
             "description": "Iron."},
            {"key": "rock_scan", "data": {"scan of": "hazard_rock", "tab": "scan"},
             "description": "A rock."},
        ]}
        science_define_scan_amd(doc)
        self.assertEqual(science_scan_tab(self.rock, "mat"), "Iron.")
        self.assertEqual(science_scan_tab(self.rock, "scan"), "A rock.")

    def test_none_doc_is_safe(self):
        science_define_scan_amd(None)   # no crash


if __name__ == "__main__":
    unittest.main()
