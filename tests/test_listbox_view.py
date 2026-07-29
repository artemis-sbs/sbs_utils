"""Listbox: the selection stays on screen across a repaint.

A repaint builds a DIFFERENT listbox -- new object, new tag, no sections until it
presents -- so a caller restoring the selection with set_selected_index(i, False)
got it held but possibly BELOW THE FOLD. The only alternative,
set_selected_index(i, True), slams it to the top on every repaint.

Two mechanisms, tested separately because they answer different questions:
`reveal_cur` guarantees VISIBILITY (automatic), and the opaque hint preserves
POSITION across the rebuild (opt-in).

Heights are NON-UNIFORM throughout. Packing walks real row heights from `cur`, so
a uniform list would hide every behaviour worth testing. Following
test_listbox_packing, the packing is asserted directly rather than through
present(), which needs a whole page context.
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest

import cosmos_dev.mock.sbs as mock_sbs
from sbs_utils.helpers import FrameContext, Context, FakeEvent
import sbs_utils.procedural.gui  # noqa: F401  (circular-import order)
from sbs_utils.pages.widgets.layout_listbox import (
    LayoutListbox, pack_slots, reveal_cur)


# Every third row is taller -- the case uniform budgeting gets wrong.
HEIGHTS = [30.0 if i % 3 == 0 else 10.0 for i in range(30)]
AVAIL = 100.0


def visible(cur, heights=HEIGHTS, avail=AVAIL):
    n = pack_slots(heights, avail, 0.0, cur)
    return list(range(cur, cur + n))


class TestReveal(unittest.TestCase):
    def test_selection_below_the_fold_is_revealed(self):
        """The reported bug: selection restored, view left at the top."""
        self.assertNotIn(25, visible(0))                  # the bug's precondition
        cur = reveal_cur(25, 0, HEIGHTS, AVAIL)
        self.assertIn(25, visible(cur))

    def test_revealed_at_the_bottom_not_the_top(self):
        """The SMALLEST move that reveals it. Scrolling it to the top is what
        set_selected_index(i, True) already does, and it makes the list jump on
        every repaint."""
        cur = reveal_cur(25, 0, HEIGHTS, AVAIL)
        self.assertEqual(visible(cur)[-1], 25)
        self.assertNotEqual(cur, 25)

    def test_selection_above_the_window_scrolls_up_to_it(self):
        cur = reveal_cur(3, 20, HEIGHTS, AVAIL)
        self.assertEqual(cur, 3)
        self.assertIn(3, visible(cur))

    def test_visible_selection_does_not_move_the_view(self):
        """The gallery's flow: the user clicked a visible row. If the reveal
        fired here, every click would shift the list under the cursor."""
        cur = 10
        sel = visible(cur)[1]
        self.assertEqual(reveal_cur(sel, cur, HEIGHTS, AVAIL), cur)

    def test_never_scrolls_past_the_end(self):
        last = len(HEIGHTS) - 1
        cur = reveal_cur(last, 0, HEIGHTS, AVAIL)
        self.assertIn(last, visible(cur))
        self.assertLessEqual(cur + pack_slots(HEIGHTS, AVAIL, 0.0, cur), len(HEIGHTS))

    def test_no_blank_space_below_when_rows_sit_above(self):
        """A view parked low in a big box drew a few rows and left the rest
        empty, with rows unseen ABOVE it. Pull back until the box is full.

        (This is what "never scroll past the end" actually means here --
        `cur + slots` can never exceed the count, because pack_slots stops at
        the end, so the naive version of this check was dead code.)"""
        big = 200.0
        sel = 26
        cur = reveal_cur(sel, 25, HEIGHTS, big)
        shown = pack_slots(HEIGHTS, big, 0.0, cur)
        self.assertIn(sel, range(cur, cur + shown))
        self.assertLess(cur, 25)                       # pulled back
        # One more row above would not have fit -- i.e. the box really is full.
        if cur > 0:
            used = sum(HEIGHTS[i] for i in range(cur, cur + shown))
            self.assertGreater(used + HEIGHTS[cur - 1], big)

    def test_out_of_range_selection_is_clamped_not_nonsense(self):
        """`sel` must index the DISPLAYED rows. A collapsible list also has an
        unfiltered index space, and passing one of those in used to send the
        back-pack past the end -- the gallery's index scrolled as though the
        list were only as long as its visible slots. Clamped now, so the worst
        case is a mildly wrong position rather than a broken scrollbar.

        NOTE: this pins the contract of reveal_cur. The _present wiring that
        chooses WHICH index to pass is not unit-testable -- presenting needs a
        whole page context -- so that side is covered by
        TestCollapsibleCoordinates asserting the two spaces differ.
        """
        cur = reveal_cur(999, 0, HEIGHTS, AVAIL)
        self.assertLess(cur, len(HEIGHTS))
        self.assertIn(len(HEIGHTS) - 1, visible(cur))

    def test_no_selection_is_left_alone(self):
        self.assertEqual(reveal_cur(None, 7, HEIGHTS, AVAIL), 7)

    def test_empty_list(self):
        self.assertEqual(reveal_cur(0, 0, [], AVAIL), 0)

    def test_box_too_small_for_the_row_still_shows_it(self):
        """avail smaller than one row: pack_slots always yields at least one, so
        the selection is still the visible row rather than nothing."""
        cur = reveal_cur(9, 0, HEIGHTS, 5.0)
        self.assertIn(9, visible(cur, avail=5.0))


class TestHint(unittest.TestCase):
    def setUp(self):
        mock_sbs.create_new_sim()
        FrameContext.context = Context(mock_sbs.sim, mock_sbs, FakeEvent())

    def _lb(self, n=30, **kw):
        items = [{"name": f"item {i}"} for i in range(n)]
        return LayoutListbox(0, 0, "lb", items, select=True, **kw)

    def test_hint_carries_selection_and_position(self):
        lb = self._lb()
        lb.cur = 12
        lb.set_selected_index(14, False)
        hint = lb.get_selection_hint()
        self.assertEqual(hint["cur"], 12)
        self.assertEqual(hint["selected_index"], 14)

    def test_hint_restores_into_a_different_listbox(self):
        old = self._lb()
        old.cur = 12
        old.set_selected_index(14, False)

        new = self._lb()                       # a DIFFERENT object
        new.apply_selection_hint(old.get_selection_hint())
        self.assertEqual(new.cur, 12)
        self.assertEqual(new._selected_index(), 14)

    def test_hint_is_a_plain_value(self):
        """The contract is "pass it along", so it must not hold the widget --
        the old listbox dies with the old page."""
        lb = self._lb()
        lb.set_selected_index(3, False)
        for v in lb.get_selection_hint().values():
            self.assertNotIsInstance(v, LayoutListbox)

    def test_stale_hint_from_a_shorter_list_is_clamped(self):
        big = self._lb(n=30)
        big.cur = 25
        big.set_selected_index(28, False)

        small = self._lb(n=5)
        small.apply_selection_hint(big.get_selection_hint())
        self.assertLess(small.cur, 5)
        self.assertIsNone(small._selected_index())   # out of range, dropped

    def test_garbage_hint_does_not_raise(self):
        lb = self._lb()
        for junk in (None, "nonsense", 42, {}, {"cur": 999, "selected_index": 999}):
            lb.apply_selection_hint(junk)
        self.assertLess(lb.cur, 30)


class TestCollapsibleCoordinates(unittest.TestCase):
    """A collapsible list has TWO index spaces and they are not interchangeable.

    `unfiltered_items` is everything; `_items` is what is on show, rebuilt each
    present with collapsed rows skipped. `set_selected_index` takes an UNFILTERED
    index; `cur`, the packer and `sections[].item_index` are all DISPLAY indices.

    Mixing them produced an index past the end of the shorter list and a nonsense
    scroll position -- the gallery's index, which is collapsible with headers,
    scrolled as though the list were only as long as the visible slots.
    """
    def setUp(self):
        mock_sbs.create_new_sim()
        FrameContext.context = Context(mock_sbs.sim, mock_sbs, FakeEvent())

    def _collapsed_lb(self):
        from sbs_utils.pages.widgets.layout_listbox import LayoutListBoxHeader
        items = []
        for h in range(3):
            items.append(LayoutListBoxHeader(f"head {h}", h == 0))   # first collapsed
            for i in range(8):
                items.append({"name": f"h{h} item {i}"})
        lb = LayoutListbox(0, 0, "lb", items, select=True, collapsible=True)
        # What present() does to build the visible list.
        lb._items = [it for it in items
                     if isinstance(it, LayoutListBoxHeader) or not items[0].collapse
                     or items.index(it) > 8]
        return lb, items

    def test_display_and_unfiltered_indices_differ(self):
        lb, items = self._collapsed_lb()
        lb.set_selected_index(len(items) - 1, False)      # last item, unfiltered
        self.assertNotEqual(lb._selected_index(), lb._selected_display_index())

    def test_display_index_is_within_the_visible_list(self):
        """The invariant the reveal depends on: the index it is handed must be a
        valid position in the list the packer measures."""
        lb, items = self._collapsed_lb()
        lb.set_selected_index(len(items) - 1, False)
        d = lb._selected_display_index()
        self.assertIsNotNone(d)
        self.assertLess(d, len(lb._items))

    def test_unfiltered_index_would_be_out_of_range(self):
        """Why it broke: the unfiltered index is past the end of the shown list,
        so back-packing from it produced a meaningless cur."""
        lb, items = self._collapsed_lb()
        lb.set_selected_index(len(items) - 1, False)
        self.assertGreaterEqual(lb._selected_index(), len(lb._items))


class TestResize(unittest.TestCase):
    """A resize is a present with different bounds, so it needs no special case
    -- the hint's cur is a hint, and the reveal has the final word."""

    def test_shrinking_past_the_selection_reveals_it_again(self):
        tall, short = 200.0, 40.0
        cur = reveal_cur(12, 0, HEIGHTS, tall)
        self.assertIn(12, visible(cur, avail=tall))
        cur = reveal_cur(12, cur, HEIGHTS, short)     # box shrank
        self.assertIn(12, visible(cur, avail=short))

    def test_growing_keeps_the_view_when_content_fills_it(self):
        """A bigger box shows MORE below; the top does not move."""
        cur = 2
        sel = visible(cur)[0]
        self.assertEqual(reveal_cur(sel, cur, HEIGHTS, 200.0), cur)

    def test_growing_past_the_end_pulls_back_instead_of_leaving_a_gap(self):
        """Near the end there is nothing below to fill the new space, so the
        view pulls UP rather than drawing a few rows against an empty box.
        (The first version of this test asserted the view never moves on a
        grow -- which is only true while content remains below.)"""
        cur = 8
        sel = visible(cur)[0]
        out = reveal_cur(sel, cur, HEIGHTS, 400.0)
        self.assertLess(out, cur)
        self.assertIn(sel, range(out, out + pack_slots(HEIGHTS, 400.0, 0.0, out)))


if __name__ == "__main__":
    unittest.main()
