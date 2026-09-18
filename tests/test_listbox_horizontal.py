"""A horizontal listbox lays its items out left to right at the `col-width` pitch.

It could not. Every item is MEASURED in a 100-wide box and a row spans its whole section,
so every item measured 100 wide - and `col-width` was ADDED to that. A horizontal list in
a box narrower than the screen therefore fitted no slots: nothing drew but the measuring
pass, parked off screen. The draw loop, meanwhile, gave each item a zero-width section,
so a flex row in the template resolved against nothing.

Now `col-width` on a horizontal listbox IS the item's width and pitch: the item's
section spans it, the next item starts one pitch later, and the slot count is the
available width over the pitch. Found building the comms filter chips (LegendaryMissions
consoles/comms_chips.py).

The harness is test_listbox_modes.py's, copied rather than imported - a sibling test
import loads the module twice.
"""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

from sbs_utils.helpers import FrameContext, Context, FakeEvent
from sbs_utils.vec import Vec3

import sbs_utils.procedural.gui  # noqa: F401  (circular-import order)
from sbs_utils.pages.widgets.layout_listbox import LayoutListbox
from sbs_utils.pages.layout.bounds import Bounds


class FakeTask:
    class _Main:
        class _Page:
            client_id = 0
        page = _Page()
    main = _Main()

    def compile_and_format_string(self, value):
        return value

    def get_variable(self, name, default=None):
        return default

    def set_variable(self, name, value):
        pass


class FakePage:
    gui_task = FakeTask()


# A band across the middle of a 1024x768 screen: 40% wide, 64px tall.
BAND = Bounds(30.0, 20.0, 70.0, 28.3)


def _chip(item, **kwargs):
    from sbs_utils.procedural.gui import gui_row, gui_text
    gui_row("row-height: 1fr;")
    gui_text(f"$text:`{item}`;justify:center;font:gui-2;")
    return None


class HorizontalBase(unittest.TestCase):
    def setUp(self):
        from cosmos_dev.mock import sbs as mock_sbs
        mock_sbs.create_new_sim()
        FrameContext.aspect_ratios[0] = Vec3(1024, 768, 0)
        FrameContext.context = Context(mock_sbs.sim, mock_sbs, FakeEvent())
        FrameContext.page = FakePage()

    def tearDown(self):
        FrameContext.page = None
        FrameContext.context = None

    def lb(self, items, pitch="7.5em", **kw):
        b = Bounds(BAND)
        lb = LayoutListbox(b.left, b.top, "lb", items, item_template=_chip, **kw)
        lb.tag = "lb"
        lb.bounds = b
        lb.client_id = 0
        # Through the style parser, exactly as `col-width:` in a listbox style arrives.
        from sbs_utils.procedural.style import apply_control_styles
        apply_control_styles("", f"col-width:{pitch};", lb, FakeTask())
        lb.horizontal = True
        lb._present(FakeEvent())
        return lb

    def sections(self, lb):
        return [s for s in (getattr(lb, "sections", []) or [])
                if getattr(s, "item_index", None) is not None]


class TestPitch(HorizontalBase):

    def test_MORE_THAN_ONE_ITEM_DRAWS(self):
        """The bug: a band narrower than 100% fitted no slots at all."""
        self.assertGreater(len(self.sections(self.lb([f"c{i}" for i in range(8)]))), 1)

    def test_items_step_left_to_right_at_the_pitch(self):
        secs = self.sections(self.lb([f"c{i}" for i in range(8)]))
        lefts = [s.bounds.left for s in secs]
        steps = {round(b - a, 3) for a, b in zip(lefts, lefts[1:])}
        self.assertEqual(1, len(steps), f"uneven pitch: {lefts}")
        self.assertGreater(steps.pop(), 0)

    def test_an_item_spans_its_pitch_rather_than_zero(self):
        """A flex row in the template needs a section with a width to fill."""
        secs = self.sections(self.lb([f"c{i}" for i in range(8)]))
        widths = {round(s.bounds.width, 3) for s in secs}
        self.assertEqual(1, len(widths))
        self.assertGreater(widths.pop(), 5)

    def test_only_what_fits_is_drawn_and_the_rest_scrolls(self):
        lb = self.lb([f"c{i}" for i in range(8)])
        shown = len(self.sections(lb))
        self.assertLess(shown, 8)
        self.assertEqual(8 - shown, lb.extra_slot_count)

    def test_every_item_stays_inside_the_band(self):
        for s in self.sections(self.lb([f"c{i}" for i in range(8)])):
            self.assertLessEqual(s.bounds.right, BAND.right + 0.01)

    def test_cur_scrolls_the_window(self):
        lb = self.lb([f"c{i}" for i in range(8)])
        lb.cur = 3
        lb._present(FakeEvent())
        self.assertEqual(3, self.sections(lb)[0].item_index)

    def test_a_wider_pitch_fits_fewer(self):
        narrow = len(self.sections(self.lb([f"c{i}" for i in range(8)], pitch="5em")))
        wide = len(self.sections(self.lb([f"c{i}" for i in range(8)], pitch="10em")))
        self.assertGreater(narrow, wide)


if __name__ == "__main__":
    unittest.main()
