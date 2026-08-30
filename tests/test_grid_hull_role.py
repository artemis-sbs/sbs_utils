"""A hull's floor plan answers "does this ship have a jump drive" IMMEDIATELY.

The blob value `jump_drive_active` is written by a mission route once the interior has
been BUILT, and interiors are built late and asynchronously - so a console that opened
first laid itself out without the drive's controls and nothing told it to look again.
Reported on a xim_dreadnought: "the initial layout they do not show up, I have to
change console back and then they show up".
"""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

from cosmos_dev.mock import sbs  # noqa: F401  (registers the sbs mock)
from sbs_utils.procedural.grid import grid_get_layout, grid_hull_has_role


class TestGridHullHasRole(unittest.TestCase):
    def test_the_xim_hulls_have_a_jump_node(self):
        for hull in ("xim_dreadnought", "xim_scout", "xim_corsair", "xim_carrier"):
            self.assertTrue(grid_hull_has_role(hull, "jump"), hull)

    def test_the_tsn_hulls_have_warp_instead(self):
        self.assertTrue(grid_hull_has_role("tsn_light_cruiser", "warp"))
        self.assertFalse(grid_hull_has_role("tsn_light_cruiser", "jump"))

    def test_a_small_craft_has_neither(self):
        self.assertFalse(grid_hull_has_role("tsn_fighter", "jump"))
        self.assertFalse(grid_hull_has_role("tsn_fighter", "warp"))

    def test_the_role_match_is_case_insensitive(self):
        """The stock data writes roles as `system,ENGINE,WARP`."""
        self.assertTrue(grid_hull_has_role("tsn_light_cruiser", "WARP"))
        self.assertTrue(grid_hull_has_role("tsn_light_cruiser", " warp "))

    def test_a_substring_is_not_a_role(self):
        """`role` matches a whole comma-separated entry, not any text in it - or
        `warp` would match a node named `warp_core` in some mod's plan."""
        self.assertFalse(grid_hull_has_role("tsn_light_cruiser", "war"))
        self.assertFalse(grid_hull_has_role("tsn_light_cruiser", "arp"))

    def test_an_unknown_hull_is_false_not_an_error(self):
        self.assertFalse(grid_hull_has_role("no_such_hull", "jump"))
        self.assertIsNone(grid_get_layout("no_such_hull"))

    def test_it_needs_no_interior_and_no_ship(self):
        """The whole point: a hull KEY answers, with nothing spawned at all."""
        self.assertTrue(grid_hull_has_role("xim_dreadnought", "jump"))


if __name__ == "__main__":
    unittest.main()
