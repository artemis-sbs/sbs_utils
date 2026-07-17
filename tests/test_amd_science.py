"""Tests for the AMD science-scan vocabulary (sbs_utils.procedural.amd_science).

Authors define per-role scans declaratively in an .amd file; amd_scan_data parses one
fence into a {tab: text} dict and science_define_scan_amd registers a whole doc.

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
    def test_labels_map_to_tabs(self):
        d = amd_scan_data("Scan: A rock.\nMat: High iron.\nBio: No life.")
        self.assertEqual(d, {"scan": "A rock.", "mat": "High iron.", "bio": "No life."})

    def test_known_labels_parsed(self):
        # standard tabs are captured; stray labels are filtered by the loader, not here
        d = amd_scan_data("Scan: A rock.\nIntel: heavy")
        self.assertEqual(d.get("scan"), "A rock.")
        self.assertEqual(d.get("intel"), "heavy")


class ScienceDefineScanAmdTests(unittest.TestCase):
    def setUp(self):
        sbs.create_new_sim()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent())
        SpaceObject.clear()
        science_clear_scan_defs()
        self.rock = to_id(npc_spawn(0, 0, 0, "Rock", "hazard_rock", "tsn_light_cruiser", "behav_npcship"))
        self.poacher = to_id(npc_spawn(0, 0, 100, "Trawler", "poacher", "tsn_light_cruiser", "behav_npcship"))

    def _doc(self):
        # mimic document_get_amd_file's parsed shape: children with key/description/data
        return {"children": [
            {"key": "hazard_rock", "description": "",
             "data": amd_scan_data("Scan: A dense asteroid.\nMat: High iron.")},
            {"key": "poacher", "description": "",
             "data": amd_scan_data("Scan: Unregistered trawler.\nIntel: Board, don't destroy.")},
        ]}

    def test_registers_each_role(self):
        science_define_scan_amd(self._doc())
        self.assertTrue(science_has_scan_def(self.rock))
        self.assertEqual(science_scan_tab(self.rock, "scan"), "A dense asteroid.")
        self.assertEqual(science_scan_tab(self.rock, "mat"), "High iron.")
        self.assertEqual(science_scan_tab(self.poacher, "intel"), "Board, don't destroy.")

    def test_prose_body_becomes_scan_when_no_scan_label(self):
        doc = {"children": [
            {"key": "hazard_rock", "description": "A drifting hulk.",
             "data": amd_scan_data("Mat: Salvageable.")},
        ]}
        science_define_scan_amd(doc)
        self.assertEqual(science_scan_tab(self.rock, "scan"), "A drifting hulk.")
        self.assertEqual(science_scan_tab(self.rock, "mat"), "Salvageable.")

    def test_loader_filters_stray_labels(self):
        doc = {"children": [
            {"key": "hazard_rock", "description": "",
             "data": amd_scan_data("Scan: A rock.\nWeight: heavy")},
        ]}
        science_define_scan_amd(doc)
        from sbs_utils.procedural.science import science_scan_def_for
        self.assertEqual(science_scan_def_for(self.rock), {"scan": "A rock."})  # no 'weight'

    def test_placeholder_value_yaml_mode_still_registers(self):
        # a {placeholder} value flips the fence to YAML (amd_is_yaml_flow triggers on '{'),
        # which preserves label CASE - the loader lowercases so it still registers, and the
        # placeholder is kept literal for scan-time interpolation.
        doc = {"children": [
            {"key": "poacher", "description": "",
             "data": amd_scan_data("Scan: A trawler.\nIntel: Registered to Captain {captain}.")},
        ]}
        science_define_scan_amd(doc)
        from sbs_utils.procedural.inventory import set_inventory_value
        set_inventory_value(self.poacher, "captain", "Vale")
        self.assertEqual(science_scan_tab(self.poacher, "scan"), "A trawler.")
        self.assertEqual(science_scan_tab(self.poacher, "intel"), "Registered to Captain Vale.")

    def test_none_doc_is_safe(self):
        science_define_scan_amd(None)   # no crash


if __name__ == "__main__":
    unittest.main()
