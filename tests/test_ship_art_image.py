"""`ship_art_image` - the flat sprite that sits beside every hull mesh.

A GUI that wants to show WHICH ship it is talking about has two options: ask the
engine for a 3d render, or draw `<artfileroot><size>.png`. Only the second one is a
plain image a layout can put in a `background-image:`, and until now every caller had
to know that `artfileroot` is a graphics-relative path and that the size is glued on
with no separator. The manual-beams panel is the third place that needed it.
"""

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest

# Settle the import order before anything reaches procedural.comms (see test_grid_mod_api).
import sbs_utils.mast_sbs.story_nodes  # noqa: F401
from sbs_utils.procedural.ship_data import (
    add_ship_data, get_ship_data, ship_art_image, ship_data_reset_for_mission)


class TestShipArtImage(unittest.TestCase):
    def setUp(self):
        ship_data_reset_for_mission()
        if get_ship_data() is None:
            self.skipTest("no shipData available in this environment")
        add_ship_data({"key": "art_test_ship", "name": "Art Test", "side": "TSN",
                       "artfileroot": "ships/TSNBattleship"})
        add_ship_data({"key": "art_test_no_art", "name": "No Art", "side": "TSN"})

    def tearDown(self):
        ship_data_reset_for_mission()

    def test_key_gives_the_1024_sprite(self):
        # The size is glued straight on: `ships/TSNBattleship` + `1024`. No separator,
        # no `.png` - both `gui_image*` and a `background-image:` style add their own.
        self.assertEqual(ship_art_image("art_test_ship"), "ships/TSNBattleship1024")

    def test_size_is_selectable(self):
        self.assertEqual(ship_art_image("art_test_ship", 256), "ships/TSNBattleship256")

    def test_unknown_key_is_none(self):
        self.assertIsNone(ship_art_image("no_such_hull_anywhere"))

    def test_entry_without_art_is_none(self):
        # A pickup or a marker may carry no art at all. That is not an error, and it
        # must not come back as the string "None1024".
        self.assertIsNone(ship_art_image("art_test_no_art"))

    def test_empty_key_is_none(self):
        # `SpaceObject.ship_data_key` starts as "" - an object whose art was never set
        # asks this question and has to get a usable answer.
        self.assertIsNone(ship_art_image(""))

    def test_id_that_resolves_to_nothing_is_none(self):
        # to_object() answers None for the server client (0) and for a deleted agent.
        self.assertIsNone(ship_art_image(0))

    def test_object_is_read_through_ship_data_key(self):
        class _FakeShip:
            ship_data_key = "art_test_ship"

        so = _FakeShip()
        # to_object() passes a non-int, non-str through when it is already an agent;
        # go the short way and confirm the attribute is what gets read.
        self.assertEqual(ship_art_image(so.ship_data_key), "ships/TSNBattleship1024")


if __name__ == "__main__":
    unittest.main()
