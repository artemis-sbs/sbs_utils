"""What a LayoutListbox actually DOES today, per mode. Characterisation, not wishes.

Written after a "keep the selection on screen" change broke the Control
Gallery's index twice. Both regressions lived in `_present` -- which index space
is passed, what the visible window means -- and the tests at the time exercised
a pure helper, so they stayed green through both. This file closes that gap:
it drives the real `_present`, in each mode, and pins what it does NOW.

Nothing here asserts an improvement. If a test in this file changes, a mode
changed -- which is the signal that was missing.

The harness (FakePage + `_present`) is lifted from test_listbox_carousel_height,
which already had it.

HORIZONTAL IS DELIBERATELY LEFT ALONE. It is reported to have bugs of its own,
so it is characterised only to the extent of "it packs by width, and it is a
distinct path" -- deliberately not pinned in detail, so nothing here can be read
as blessing its current behaviour.
"""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

from sbs_utils.helpers import FrameContext, Context, FakeEvent
from sbs_utils.vec import Vec3

import sbs_utils.procedural.gui  # noqa: F401  (circular-import order)
from sbs_utils.pages.widgets.layout_listbox import (
    LayoutListbox, LayoutListBoxHeader)
from sbs_utils.pages.layout.bounds import Bounds


class FakeTask:
    """The little a row template touches: styles resolve an aspect ratio through
    task.main.page.client_id, and gui_text formats its props through the task.

    The carousel test gets away with `gui_task = None` because its template
    builds nothing. Real row heights need real gui_row/gui_text, and packing is
    the whole subject here -- with a no-op template every row is 0 high and the
    entire list "fits", which would make every windowing assertion vacuous.
    """
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
    """Only what LayoutListbox._present reads off the enclosing page."""
    gui_task = FakeTask()


PANEL = Bounds(2.0, 10.0, 30.0, 90.0)


class ListboxModeBase(unittest.TestCase):
    def setUp(self):
        from cosmos_dev.mock import sbs as mock_sbs
        mock_sbs.create_new_sim()
        FrameContext.aspect_ratios[0] = Vec3(1024, 768, 0)
        FrameContext.context = Context(mock_sbs.sim, mock_sbs, FakeEvent())
        FrameContext.page = FakePage()

    def tearDown(self):
        FrameContext.page = None
        FrameContext.context = None

    @staticmethod
    def _template(item, **kwargs):
        from sbs_utils.procedural.gui import gui_row, gui_text
        gui_row("row-height: 1.2em;")
        label = item.label if isinstance(item, LayoutListBoxHeader) else str(item)
        gui_text(f"$text:`{label}`;font:gui-2;")
        return None

    def _lb(self, items, bounds=None, **kw):
        b = Bounds(bounds or PANEL)
        lb = LayoutListbox(b.left, b.top, "lb", items,
                           item_template=self._template, **kw)
        lb.tag = "lb"
        lb.bounds = b
        lb.client_id = 0
        return lb

    def _shown(self, lb):
        """Item indices actually drawn -- the table on_click resolves against."""
        return [s.item_index for s in (getattr(lb, "sections", []) or [])
                if getattr(s, "item_index", None) is not None]


class TestPlainVertical(ListboxModeBase):
    """The common case, and the one a naive change is designed against."""

    def test_shows_a_window_starting_at_cur(self):
        lb = self._lb([f"item {i}" for i in range(40)])
        lb._present(FakeEvent())
        shown = self._shown(lb)
        self.assertTrue(shown)
        self.assertEqual(shown[0], 0)
        self.assertLess(len(shown), 40, "a 40-item list must not all fit")

    def test_cur_moves_the_window(self):
        lb = self._lb([f"item {i}" for i in range(40)])
        lb.cur = 10
        lb._present(FakeEvent())
        self.assertEqual(self._shown(lb)[0], 10)

    def test_selection_off_screen_is_NOT_revealed_today(self):
        """The reported bug, pinned as current behaviour so the fix has
        something to change."""
        lb = self._lb([f"item {i}" for i in range(40)], select=True)
        lb.set_selected_index(35, False)
        lb._present(FakeEvent())
        self.assertNotIn(35, self._shown(lb))


class TestCollapsible(ListboxModeBase):
    """Two index spaces. `unfiltered_items` is everything; `_items` is what is
    shown, rebuilt each present with collapsed rows skipped. This is the mode
    that broke -- the gallery's index is the only one like it in the tree."""

    def _items(self, collapse_first):
        items = []
        for h in range(3):
            items.append(LayoutListBoxHeader(f"head {h}", h == 0 and collapse_first))
            for i in range(6):
                items.append(f"h{h} item {i}")
        return items

    def test_collapsed_rows_are_dropped_from_the_shown_list(self):
        items = self._items(True)
        lb = self._lb(items, collapsible=True)
        lb._present(FakeEvent())
        self.assertLess(len(lb._items), len(lb.unfiltered_items))

    def test_expanded_shows_everything_it_has_room_for(self):
        lb = self._lb(self._items(False), collapsible=True)
        lb._present(FakeEvent())
        self.assertEqual(len(lb._items), len(lb.unfiltered_items))

    def test_item_index_indexes_the_SHOWN_list(self):
        """on_click ends at `self.items[index]`, so a slot's item_index is a
        display index -- NOT an index into unfiltered_items. Mixing the two is
        exactly what broke the gallery."""
        items = self._items(True)
        lb = self._lb(items, collapsible=True, select=True)
        lb._present(FakeEvent())
        for idx in self._shown(lb):
            self.assertLess(idx, len(lb._items))

    def test_the_two_spaces_genuinely_diverge(self):
        items = self._items(True)
        lb = self._lb(items, collapsible=True, select=True)
        lb._present(FakeEvent())
        last_shown = lb._items[-1]
        self.assertNotEqual(lb.unfiltered_items.index(last_shown),
                            lb._items.index(last_shown))


class TestCarousel(ListboxModeBase):
    """One item IS the window, so "how many fit" is meaningless here."""

    def test_shows_exactly_one(self):
        lb = self._lb([f"item {i}" for i in range(10)], carousel=True)
        lb._present(FakeEvent())
        self.assertEqual(len(self._shown(lb)), 1)

    def test_cur_selects_which_one(self):
        lb = self._lb([f"item {i}" for i in range(10)], carousel=True)
        lb.cur = 4
        lb._present(FakeEvent())
        self.assertEqual(self._shown(lb), [4])


class TestMultiSelect(ListboxModeBase):
    def test_several_can_be_selected(self):
        lb = self._lb([f"item {i}" for i in range(10)], select=True, multi=True)
        lb._present(FakeEvent())
        lb.selected = [lb._items[1], lb._items[3]]
        self.assertEqual(len(lb.get_selected()), 2)


class TestReadOnly(ListboxModeBase):
    def test_read_only_still_draws(self):
        lb = self._lb([f"item {i}" for i in range(10)], read_only=True)
        lb._present(FakeEvent())
        self.assertTrue(self._shown(lb))


class TestHorizontalIsLeftAlone(ListboxModeBase):
    """Reported to have bugs of its own. Pinned ONLY as "a distinct path that
    draws", so nothing here blesses its behaviour or blocks fixing it later."""

    def test_it_is_a_separate_packing_path(self):
        lb = self._lb([f"item {i}" for i in range(10)])
        lb.horizontal = True
        lb._present(FakeEvent())          # must not raise
        self.assertIsNotNone(getattr(lb, "sections", None))


if __name__ == "__main__":
    unittest.main()
