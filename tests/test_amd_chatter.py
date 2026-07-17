"""amd_chatter - author radio/dispatch/news barks as declarative AMD line-pools; read a section
into {key: [lines]} pools and pick one at random with {field} interpolation.

Run: python -m unittest tests.test_amd_chatter
"""
import unittest
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import sbs_utils.mast_sbs.story_nodes  # import first to break a circular import
from sbs_utils.procedural.amd_chatter import (
    chatter_scenes, chatter_line, amd_chatter_data)


def _section():
    # mimic document_get_amd_file's parsed shape: children with key/display_text/description
    return {"children": [
        {"key": "ack_strike", "display_text": "Order: Strike",
         "description": "Weapons free. Moving to engage.\nGuns hot, Admiral - closing now."},
        {"key": "salvage_haul", "display_text": "Salvage Haul",
         "description": "Wreck stripped: +{ore} ore, +{gas} gas."},
        {"key": "formed", "display_text": "Formed",
         "description": "% Fleet formed and standing by.\n// a comment line, ignored\n%Assembled and ready."},
        {"key": "empty", "display_text": "Empty", "description": ""},
    ]}


class AmdChatterTests(unittest.TestCase):
    def test_pool_read_from_body(self):
        scenes = chatter_scenes(_section())
        self.assertEqual(scenes["ack_strike"],
                         ["Weapons free. Moving to engage.", "Guns hot, Admiral - closing now."])
        # empty-body heading is skipped
        self.assertNotIn("empty", scenes)

    def test_percent_marker_and_comment_stripped(self):
        scenes = chatter_scenes(_section())
        # leading % stripped (with or without a space); // comment line dropped
        self.assertEqual(scenes["formed"], ["Fleet formed and standing by.", "Assembled and ready."])

    def test_random_pick_stays_in_pool(self):
        scenes = chatter_scenes(_section())
        pool = set(scenes["ack_strike"])
        for _ in range(200):
            self.assertIn(chatter_line(scenes, "ack_strike"), pool)

    def test_field_interpolation(self):
        scenes = chatter_scenes(_section())
        self.assertEqual(chatter_line(scenes, "salvage_haul", ore=5, gas=3),
                         "Wreck stripped: +5 ore, +3 gas.")

    def test_unknown_field_left_literal(self):
        scenes = chatter_scenes(_section())
        # gas not supplied -> {gas} stays literal, no crash
        self.assertEqual(chatter_line(scenes, "salvage_haul", ore=5),
                         "Wreck stripped: +5 ore, +{gas} gas.")

    def test_missing_key_safe(self):
        scenes = chatter_scenes(_section())
        self.assertEqual(chatter_line(scenes, "not_a_key"), "")
        self.assertEqual(chatter_line(scenes, "empty"), "")

    def test_none_section_safe(self):
        self.assertEqual(chatter_scenes(None), {})
        self.assertEqual(chatter_line(None, "ack_strike"), "")

    def test_data_parser_default_coercion(self):
        d = amd_chatter_data("Title: dispatch")
        self.assertEqual(d.get("title"), "dispatch")


if __name__ == "__main__":
    unittest.main()
