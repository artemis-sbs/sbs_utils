"""Every selected row of a multi-select listbox gets its own selection tick.

The tick was sent under the LISTBOX's tag - one tag for every row - so in a multi-select
each tick replaced the one before it and at most one row ever looked selected. Found on
the comms filter chips (LegendaryMissions consoles/comms_chips.py), where tapping two
chips left one visibly selected.

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


def _row(item, **kwargs):
    from sbs_utils.procedural.gui import gui_row, gui_text
    gui_row("row-height: 1.2em;")
    gui_text(f"$text:`{item}`;font:gui-2;")
    return None


class TestTicks(unittest.TestCase):
    def setUp(self):
        from cosmos_dev.mock import sbs as mock_sbs
        self.mock = mock_sbs
        mock_sbs.create_new_sim()
        FrameContext.aspect_ratios[0] = Vec3(1024, 768, 0)
        FrameContext.context = Context(mock_sbs.sim, mock_sbs, FakeEvent())
        FrameContext.page = FakePage()
        self.ticks = []
        self.rects = []
        self._orig = mock_sbs.send_gui_image

        def rec(cid, parent, tag, props, l, t, r, b):
            if tag.startswith("__selbg:"):
                self.ticks.append((tag, round(t, 2)))
                self.rects.append((l, t, r, b))
            return self._orig(cid, parent, tag, props, l, t, r, b)
        mock_sbs.send_gui_image = rec

    def tearDown(self):
        self.mock.send_gui_image = self._orig
        FrameContext.page = None
        FrameContext.context = None

    def present(self, items, selected, **kw):
        b = Bounds(2.0, 10.0, 30.0, 90.0)
        lb = LayoutListbox(b.left, b.top, "lb", items, item_template=_row, **kw)
        lb.tag = "lb"
        lb.bounds = b
        lb.client_id = 0
        lb.selected = list(selected)
        lb._present(FakeEvent())
        return lb

    def test_TWO_SELECTED_ROWS_SEND_TWO_DISTINCT_TICKS(self):
        self.present(["a", "b", "c", "d"], ["b", "d"], select=True, multi=True)
        self.assertEqual(2, len(self.ticks))
        self.assertEqual(2, len({tag for tag, _ in self.ticks}),
                         f"ticks share a tag, so one replaces the other: {self.ticks}")

    def test_each_tick_sits_on_its_own_row(self):
        self.present(["a", "b", "c", "d"], ["b", "d"], select=True, multi=True)
        self.assertEqual(2, len({top for _, top in self.ticks}))

    def test_vertical_tick_is_a_strip_down_the_left(self):
        self.present(["a", "b", "c"], ["b"], select=True)
        l, t, r, b = self.rects[0]
        self.assertGreater(b - t, r - l, "vertical tick should be taller than wide")

    def test_HORIZONTAL_TICK_IS_A_STRIP_ACROSS_THE_TOP(self):
        from sbs_utils.procedural.style import apply_control_styles
        b = Bounds(30.0, 20.0, 70.0, 28.3)
        lb = LayoutListbox(b.left, b.top, "lb", ["a", "b", "c", "d"], item_template=_row,
                           select=True, multi=True)
        lb.tag = "lb"
        lb.bounds = b
        lb.client_id = 0
        apply_control_styles("", "col-width:6em;", lb, FakeTask())
        lb.horizontal = True
        lb.selected = ["b"]
        lb._present(FakeEvent())
        self.assertEqual(1, len(self.rects))
        l, t, r, bot = self.rects[0]
        sec = [s for s in lb.sections if s.item_index == 1][0]
        self.assertAlmostEqual(sec.bounds.left, l, places=3)
        self.assertLess(r, sec.bounds.right, "the bar should stop short of the right edge")
        self.assertAlmostEqual(sec.bounds.top, t, places=3)
        self.assertGreater(r - l, bot - t, "horizontal tick should be wider than tall")

    def test_neighboring_horizontal_bars_do_not_touch(self):
        """Two adjacent selected chips must read as two bars, not one long one."""
        from sbs_utils.procedural.style import apply_control_styles
        b = Bounds(30.0, 20.0, 70.0, 28.3)
        lb = LayoutListbox(b.left, b.top, "lb", ["a", "b", "c", "d"], item_template=_row,
                           select=True, multi=True)
        lb.tag = "lb"
        lb.bounds = b
        lb.client_id = 0
        apply_control_styles("", "col-width:6em;", lb, FakeTask())
        lb.horizontal = True
        lb.selected = ["a", "b"]
        lb._present(FakeEvent())
        first, second = sorted(self.rects)
        self.assertLess(first[2], second[0])

    def test_single_select_still_sends_one(self):
        self.present(["a", "b", "c"], ["c"], select=True)
        self.assertEqual(1, len(self.ticks))


if __name__ == "__main__":
    unittest.main()
