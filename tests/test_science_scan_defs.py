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
from sbs_utils.procedural.inventory import set_inventory_value
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

    def test_interpolation_from_inventory(self):
        # a role TEMPLATE resolves per object from inventory
        science_define_scan("hazard_rock", {"intel": "Registered to Captain {captain}."})
        set_inventory_value(self.rock, "captain", "Vale")
        self.assertEqual(science_scan_tab(self.rock, "intel"), "Registered to Captain Vale.")

    def test_interpolation_unknown_key_left_literal(self):
        science_define_scan("hazard_rock", {"intel": "Captain {captain}."})
        # no 'captain' inventory -> placeholder left as-is (harmless), not a crash
        self.assertEqual(science_scan_tab(self.rock, "intel"), "Captain {captain}.")

    def test_per_object_override_wins(self):
        science_define_scan("hazard_rock", {"scan": "Generic asteroid."})
        set_inventory_value(self.rock, "scan_scan", "THIS specific rock is unstable.")
        self.assertEqual(science_scan_tab(self.rock, "scan"), "THIS specific rock is unstable.")

    def test_override_makes_scannable_without_role_def(self):
        # a per-object override alone (no role def) is enough to be scannable
        set_inventory_value(self.ship, "scan_bio", "Crew of 40, all healthy.")
        self.assertTrue(science_has_scan_def(self.ship))
        self.assertEqual(science_scan_tab(self.ship, "bio"), "Crew of 40, all healthy.")

    def test_list_value_is_random_one_of(self):
        # a list tab value = %-style random variants; each read is one of them
        science_define_scan("hazard_rock", {"scan": ["A rock.", "A boulder.", "A hulk."]})
        opts = {"A rock.", "A boulder.", "A hulk."}
        for _ in range(20):
            self.assertIn(science_scan_tab(self.rock, "scan"), opts)

    def test_list_variant_still_interpolates(self):
        science_define_scan("hazard_rock", {"intel": ["Captain {captain}.", "Skipper {captain}."]})
        set_inventory_value(self.rock, "captain", "Vale")
        self.assertIn(science_scan_tab(self.rock, "intel"), ["Captain Vale.", "Skipper Vale."])


if __name__ == "__main__":
    unittest.main()
