"""Tests for declarative per-role science-scan content (science_define_scan et al).

Register scan text for a role; any object holding that role reports that content, so a
generic //science route can render it - no hand-authored route per object type. This is
the object-level twin of the quest `reveal_scan`.

Run: python -m unittest tests.test_science_scan_defs
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
from sbs_utils.procedural.science import (
    science_define_scan, science_clear_scan_defs, science_scan_def_for,
    science_has_scan_def, science_scan_tab)


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


class ScienceScanDefTests(unittest.TestCase):
    def setUp(self):
        sbs.create_new_sim()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent())
        SpaceObject.clear()
        science_clear_scan_defs()
        self.rock = to_id(npc_spawn(0, 0, 0, "Rock", "hazard_rock", "tsn_light_cruiser", "behav_npcship"))
        self.ship = to_id(npc_spawn(0, 0, 100, "Ship", "tsn", "tsn_light_cruiser", "behav_npcship"))

    def test_string_is_scan_tab(self):
        science_define_scan("hazard_rock", "A dense asteroid.")
        self.assertEqual(science_scan_tab(self.rock, "scan"), "A dense asteroid.")
        self.assertEqual(science_scan_def_for(self.rock), {"scan": "A dense asteroid."})

    def test_multi_tab_dict(self):
        science_define_scan("hazard_rock", {"scan": "Asteroid.", "mat": "High iron."})
        self.assertTrue(science_has_scan_def(self.rock))
        self.assertEqual(science_scan_tab(self.rock, "mat"), "High iron.")
        self.assertEqual(science_scan_tab(self.rock, "bio"), "")   # undefined tab -> ""

    def test_undefined_role_has_nothing(self):
        science_define_scan("hazard_rock", "Asteroid.")
        self.assertFalse(science_has_scan_def(self.ship))
        self.assertEqual(science_scan_def_for(self.ship), {})
        self.assertEqual(science_scan_tab(self.ship, "scan"), "")

    def test_defs_merge_across_calls_and_roles(self):
        science_define_scan("hazard_rock", {"scan": "Asteroid."})
        science_define_scan("hazard_rock", {"mat": "High iron."})   # merges, not replaces
        self.assertEqual(science_scan_def_for(self.rock), {"scan": "Asteroid.", "mat": "High iron."})

    def test_clear(self):
        science_define_scan("hazard_rock", "Asteroid.")
        science_clear_scan_defs()
        self.assertFalse(science_has_scan_def(self.rock))


if __name__ == "__main__":
    unittest.main()
