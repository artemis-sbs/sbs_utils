"""A CAROUSEL item gets the panel's height; a stacked item is content-sized.

The bug this pins: every listbox item section was created with `bottom == top`
-- zero height -- and grown afterwards by resize_to_content(). For a stacked
list that is right: the item is as tall as its rows. But a carousel shows
exactly ONE item, so the item IS the panel, and a zero-height section means
nothing in the template can be sized against it: a flex row resolves to 0, so
the only thing that works is a FIXED height.

A fixed height does not shrink with the window. LM's mission picker sized its
description row at `15em` -- correct in a 768-tall window, and at 1024x600 the
same 360px put the text's box at 108% of the screen, off the bottom. Measured
with `mission_runner --audit-layout --aspect`.

These tests assert the SECTION GEOMETRY the template is handed, because that is
where the bug lives -- everything downstream is just rows dividing up whatever
height they were given.
"""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

from sbs_utils.helpers import FrameContext, Context, FakeEvent
from sbs_utils.vec import Vec3

import sbs_utils.procedural.gui  # noqa: F401  (circular-import order)
from sbs_utils.pages.widgets.layout_listbox import LayoutListbox
from sbs_utils.pages.layout.bounds import Bounds


class FakePage:
    """Only what LayoutListbox._present reads off the enclosing page."""
    gui_task = None


class TestCarouselItemHeight(unittest.TestCase):
    def setUp(self):
        from cosmos_dev.mock import sbs as mock_sbs
        mock_sbs.create_new_sim()
        FrameContext.aspect_ratios[0] = Vec3(1024, 768, 0)
        FrameContext.context = Context(mock_sbs.sim, mock_sbs, FakeEvent())
        FrameContext.page = FakePage()
        self.handed = []

    def tearDown(self):
        FrameContext.page = None
        FrameContext.context = None

    def _template(self, item, **kwargs):
        # Record the section the listbox hands the template, and return None so
        # the listbox keeps its own sizing path (returning a size is what leaves
        # an item degenerate -- see GUI.md).
        #
        # calc_max runs the template FIRST against a throwaway 0,0,100,100
        # section just to measure; only the draw pass carries real geometry.
        sec = kwargs["section"]
        if sec.tag != "unused":
            self.handed.append(Bounds(sec.bounds))
        return None

    def _listbox(self, carousel, bounds):
        lb = LayoutListbox(bounds.left, bounds.top, "lb",
                           ["one", "two", "three"],
                           item_template=self._template, carousel=carousel)
        lb.tag = "lb"
        lb.bounds = bounds
        lb.client_id = 0
        return lb

    PANEL = Bounds(2.0, 30.0, 48.0, 95.0)          # the LM picker's box

    def test_carousel_item_is_given_the_panel(self):
        lb = self._listbox(True, Bounds(self.PANEL))
        lb._present(FakeEvent())

        self.assertEqual(1, len(self.handed), "a carousel presents one item")
        sec = self.handed[0]
        self.assertGreater(sec.height, 0,
                           "a zero-height section makes every flex row collapse")
        self.assertLess(sec.bottom, self.PANEL.bottom,
                        "the nav band must be held back, or content draws "
                        "under the prev/next buttons")

    def test_a_stacked_item_still_starts_content_sized(self):
        # The other 99% of listboxes must not move: a stacked item is sized by
        # its rows and grown by resize_to_content, not handed the whole panel.
        lb = self._listbox(False, Bounds(self.PANEL))
        lb._present(FakeEvent())

        self.assertTrue(self.handed)
        for sec in self.handed:
            self.assertEqual(0.0, sec.height)

    def test_the_carousel_item_tracks_the_window(self):
        """The regression itself: the item's height has to come from the panel,
        so a shorter screen produces a shorter item instead of the same fixed
        pixel block running off the bottom."""
        heights = {}
        for h in (768, 600, 480):
            FrameContext.aspect_ratios[0] = Vec3(1024, h, 0)
            self.handed = []
            lb = self._listbox(True, Bounds(self.PANEL))
            lb._present(FakeEvent())
            heights[h] = self.handed[0].height

        # Percent-of-screen: the nav band is a fixed pixel size, so it eats a
        # LARGER share of a shorter screen -- the item is relatively smaller.
        self.assertGreater(heights[768], heights[600])
        self.assertGreater(heights[600], heights[480])
        # ...and never inverts into a negative/degenerate box.
        self.assertGreater(heights[480], 0)


if __name__ == "__main__":
    unittest.main()
