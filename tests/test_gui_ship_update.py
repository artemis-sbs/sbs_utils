"""A scripted change to a gui_ship must repaint the model.

`Ship` was the last value-bearing widget whose `update()` and `value` setter wrote the
value and stopped: nothing dirty-marked, so nothing re-sent `send_gui_3dship` and the hull
only changed when something else forced a full page present. Same hole `Face` and
`TextInput` each had - see `Face.update` and tests/test_gui_input_update.py.

Found while building the TNG mod's bake walk, which swaps the hull once a second under a
page it deliberately does not rebuild. Rebuilding was the workaround, and it cost the walk:
the repaint ends the tasks hosted on the GUI task, so the walker killed itself on its own
first step.

    python -m unittest tests.test_gui_ship_update
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest

from sbs_utils.pages.layout.dirty import Dirty
from sbs_utils.pages.layout.ship import Ship

CID = 7


def _ship(hull="tsn_light_cruiser"):
    w = Ship("204", hull)
    w.client_id = CID          # Dirty.mark_dirty ignores a client-less item
    return w


def _dirty(w):
    return w in Dirty.dirty.get(CID, set())


class ShipUpdateTests(unittest.TestCase):

    def setUp(self):
        Dirty.dirty = {}

    # --- construction (unchanged behavior, pinned) -------------------------

    def test_constructor_stores_the_hull(self):
        self.assertEqual("tsn_light_cruiser", _ship().value)

    def test_constructor_adds_the_hull_tag_prefix(self):
        self.assertEqual("hull_tag:tsn_light_cruiser", _ship()._ship)

    def test_constructor_keeps_an_explicit_hull_tag(self):
        self.assertEqual("hull_tag:kralien_cruiser", Ship("204", "hull_tag:kralien_cruiser")._ship)

    def test_constructor_does_not_dirty_mark(self):
        # Marking during __init__ would enqueue a widget that is not in a layout yet.
        self.assertFalse(_dirty(_ship()))

    # --- update() ----------------------------------------------------------

    def test_update_changes_the_hull(self):
        w = _ship()
        w.update("tng_fed_galaxy")
        self.assertEqual("tng_fed_galaxy", w.value)

    def test_update_dirty_marks(self):
        w = _ship()
        w.update("tng_fed_galaxy")
        self.assertTrue(_dirty(w), "update() must dirty-mark or the model never repaints")

    def test_update_of_a_script_hidden_widget_does_not_dirty_mark(self):
        w = _ship()
        w._show = False        # is_hidden_by_script is derived, not settable
        w.update("tng_fed_galaxy")
        self.assertFalse(_dirty(w))

    # --- the value setter, which callers use far more often -----------------

    def test_value_setter_changes_the_hull(self):
        w = _ship()
        w.value = "tng_klg_vorcha"
        self.assertEqual("tng_klg_vorcha", w.value)

    def test_value_setter_dirty_marks(self):
        w = _ship()
        w.value = "tng_klg_vorcha"
        self.assertTrue(_dirty(w), "`widget.value = x` must repaint, like every other widget")


if __name__ == "__main__":
    unittest.main()
