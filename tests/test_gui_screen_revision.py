"""`gui_screen_revision` - what an `on change` watches to rebuild after a RESIZE.

A console that decides anything from the screen reads it while BUILDING, so the answer
is baked into the page. The engine's `screen_size` event updates the aspect ratio and
re-presents - which recomputes percentages but does NOT re-run the builder - so those
decisions stayed as they were.

Reported from a bridge: Engineering's orders box shows three rows on a short screen and
five on a tall one, and resizing to a tall window kept the three-row box.

    python -m unittest discover -s tests -p "test_gui_screen_revision.py"
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest

from sbs_utils.helpers import FrameContext
from sbs_utils.procedural.gui.console import (gui_screen_revision,
                                              GUI_SCREEN_BAND_PX)
from sbs_utils.vec import Vec3

CID = 7


class _Base(unittest.TestCase):
    def tearDown(self):
        FrameContext.aspect_ratios.pop(CID, None)

    def at(self, w, h, **kw):
        FrameContext.aspect_ratios[CID] = Vec3(w, h, 1)
        return gui_screen_revision(CID, **kw)


class ItChangesWhenTheLayoutWould(_Base):
    def test_a_resize_across_a_round_threshold_changes_it(self):
        """The case that was broken: 720 -> 1080 must rebuild."""
        self.assertNotEqual(self.at(1280, 720), self.at(1920, 1080))

    def test_the_1000px_boundary_is_a_band_edge(self):
        """Engineering switches row count at 1000px tall, so 999 and 1000 must be
        different revisions or the rebuild never fires at the number that matters."""
        self.assertNotEqual(self.at(1600, 999), self.at(1600, 1000))

    def test_width_alone_changing_is_noticed(self):
        self.assertNotEqual(self.at(1280, 720), self.at(1920, 720))


class ItIsCoarseOnPurpose(_Base):
    """The raw size is reported many times while a window is dragged, and a console
    rebuild per distinct value would thrash."""

    def test_a_few_pixels_inside_a_band_is_the_same_revision(self):
        self.assertEqual(self.at(1920, 1080), self.at(1920 + 5, 1080 + 5))

    def test_a_drag_across_one_band_is_one_change(self):
        seen = {self.at(1600, 1000 + n) for n in range(0, GUI_SCREEN_BAND_PX)}
        self.assertEqual(len(seen), 1, "a drag inside one band rebuilt more than once")

    def test_a_bigger_band_is_coarser(self):
        self.assertEqual(self.at(1920, 1080, band=1000),
                         self.at(1920, 1040, band=1000))


class ItDoesNotRaise(_Base):
    def test_a_client_with_no_reported_size_answers_something_stable(self):
        FrameContext.aspect_ratios.pop(CID, None)
        self.assertEqual(gui_screen_revision(CID), gui_screen_revision(CID))

    def test_a_zero_band_does_not_divide_by_zero(self):
        self.assertIsNotNone(self.at(1920, 1080, band=0))

    def test_a_zero_sized_screen_does_not_raise(self):
        self.assertIsNotNone(self.at(0, 0))


if __name__ == "__main__":
    unittest.main()
