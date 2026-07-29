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


class TestRevealOptIn(ListboxModeBase):
    """The fix, driven through the real _present -- the gap that let two
    regressions through when the tests exercised a pure helper instead."""

    def test_off_screen_selection_is_revealed_when_asked(self):
        lb = self._lb([f"item {i}" for i in range(40)], select=True, reveal=True)
        lb.set_selected_index(35, False)
        lb._present(FakeEvent())
        self.assertIn(35, self._shown(lb))

    def test_revealed_at_the_bottom_not_the_top(self):
        """Smallest move. Slamming it to the top is what
        set_selected_index(i, True) already does, and it jumps every repaint."""
        lb = self._lb([f"item {i}" for i in range(40)], select=True, reveal=True)
        lb.set_selected_index(35, False)
        lb._present(FakeEvent())
        self.assertEqual(self._shown(lb)[-1], 35)
        self.assertNotEqual(lb.cur, 35)

    def test_a_visible_selection_does_not_move_the_view(self):
        """The gallery's flow: the user clicked a visible row. If this moved,
        every click would shift the list under the cursor."""
        lb = self._lb([f"item {i}" for i in range(40)], select=True, reveal=True)
        lb.cur = 5
        lb._present(FakeEvent())
        target = self._shown(lb)[1]
        lb.set_selected_index(target, False)
        lb._present(FakeEvent())
        self.assertEqual(lb.cur, 5)

    def test_selection_above_the_window_scrolls_up(self):
        lb = self._lb([f"item {i}" for i in range(40)], select=True, reveal=True)
        lb.cur = 20
        lb.set_selected_index(2, False)
        lb._present(FakeEvent())
        self.assertIn(2, self._shown(lb))

    def test_last_item_is_reachable(self):
        lb = self._lb([f"item {i}" for i in range(40)], select=True, reveal=True)
        lb.set_selected_index(39, False)
        lb._present(FakeEvent())
        self.assertIn(39, self._shown(lb))

    def test_collapsible_reveal_uses_the_DISPLAY_index(self):
        """The regression, isolated.

        Collapse the FIRST group and a row near the top of the shown list has a
        much larger UNFILTERED index. It is already visible, so the view must not
        move -- but handed the unfiltered index the reveal believes it is far
        below the fold and scrolls to it.

        Needs a SMALL panel: with a window big enough for the whole shown list
        nothing ever scrolls, and both indices give the same answer. That is why
        the first version of this test passed under mutation.
        """
        items = [LayoutListBoxHeader("head 0", True)]           # collapsed
        items += [f"h0 item {i}" for i in range(12)]
        items += [LayoutListBoxHeader("head 1", False)]
        items += [f"h1 item {i}" for i in range(12)]
        lb = self._lb(items, bounds=Bounds(2.0, 10.0, 30.0, 30.0),
                      collapsible=True, select=True, reveal=True)
        lb._present(FakeEvent())

        shown = self._shown(lb)
        self.assertLess(len(shown), len(lb._items),
                        "the window must be smaller than the shown list")

        target = lb._items[2]                                   # first h1 row
        d = lb._items.index(target)
        u = lb.unfiltered_items.index(target)
        self.assertGreater(u, max(shown), "unfiltered index must fall outside "
                                          "the window, or nothing distinguishes")
        self.assertIn(d, shown, "display index is inside the window")

        lb.selected = [target]
        lb.cur = 0
        lb._present(FakeEvent())
        self.assertEqual(lb.cur, 0, "a visible row must not move the view")

    def test_collapsible_reveal_stays_in_the_shown_list(self):
        """The regression that broke the gallery: the reveal was handed an
        UNFILTERED index, which points past the end of the shown list once a
        header is collapsed."""
        items = []
        for h in range(3):
            items.append(LayoutListBoxHeader(f"head {h}", h == 0))
            for i in range(6):
                items.append(f"h{h} item {i}")
        lb = self._lb(items, collapsible=True, select=True, reveal=True)
        lb._present(FakeEvent())
        lb.selected = [lb._items[-1]]          # last SHOWN row
        lb._present(FakeEvent())
        self.assertLess(lb.cur, len(lb._items))
        self.assertIn(len(lb._items) - 1, self._shown(lb))


class TestScrolling(ListboxModeBase):
    """Driven through on_scroll -- the REAL path a scrollbar drag takes.

    Every other test here sets `lb.cur` directly, which is not scrolling: it
    skips on_scroll entirely. That gap is why "reveal on every present" shipped
    and made the list unscrollable -- the view snapped back to the selection on
    the very next frame, so it appeared stuck on its first screenful.
    """

    SMALL = Bounds(2.0, 10.0, 30.0, 26.0)   # window MUCH shorter than the list

    def _scroll_to(self, lb, index):
        """What the engine sends when the scrollbar moves. The slider value is
        inverted about extra_slot_count for a vertical list -- see on_scroll."""
        ev = FakeEvent()
        ev.sub_tag = f"{lb.tag_prefix}cur"
        ev.sub_float = float(-index + lb.extra_slot_count + 0.5)
        lb.on_message(ev)
        return lb.cur

    def test_scrolling_moves_the_view(self):
        lb = self._lb([f"item {i}" for i in range(40)])
        lb._present(FakeEvent())
        self.assertEqual(self._scroll_to(lb, 12), 12)

    def test_scrolling_away_from_the_selection_STICKS(self):
        """The reported bug: with reveal on, the view was dragged back to the
        selection on the next present, so the list could not be scrolled past
        its first screenful."""
        lb = self._lb([f"item {i}" for i in range(40)], select=True, reveal=True)
        lb.set_selected_index(0, False)
        lb._present(FakeEvent())            # reveal fires once, view at the top

        self._scroll_to(lb, 20)
        lb._present(FakeEvent())            # must NOT snap back
        self.assertEqual(lb.cur, 20)
        self.assertNotIn(0, self._shown(lb))

    def test_a_new_selection_re_arms_the_reveal(self):
        """Scrolling wins over the reveal, but choosing something new does not
        leave you looking at the wrong place.

        SMALL panel deliberately: with a window big enough to hold both the
        scrolled-to position and the new selection, this passes whether or not
        the re-arm exists. (It did, first time round.)"""
        lb = self._lb([f"item {i}" for i in range(40)], bounds=self.SMALL,
                      select=True, reveal=True)
        lb._present(FakeEvent())
        self._scroll_to(lb, 5)
        lb._present(FakeEvent())
        self.assertNotIn(35, self._shown(lb), "must start out of view")

        lb.set_selected_index(35, False)
        lb._present(FakeEvent())
        self.assertIn(35, self._shown(lb))

    def test_scrolling_before_the_frame_renders_still_wins(self):
        """The ordering the disarm exists for: a selection arms the reveal, the
        user scrolls, and the frame has not been drawn yet. The scroll is the
        later instruction, so it wins."""
        lb = self._lb([f"item {i}" for i in range(40)], bounds=self.SMALL,
                      select=True, reveal=True)
        lb._present(FakeEvent())
        lb.set_selected_index(35, False)        # arms the reveal
        self._scroll_to(lb, 2)                  # ...then the user scrolls
        lb._present(FakeEvent())
        self.assertEqual(lb.cur, 2)
        self.assertNotIn(35, self._shown(lb))

    def test_scrolling_without_reveal_is_unchanged(self):
        lb = self._lb([f"item {i}" for i in range(40)], select=True)
        lb._present(FakeEvent())
        self._scroll_to(lb, 15)
        lb._present(FakeEvent())
        self.assertEqual(lb.cur, 15)


class TestHintKeepsTheRowUnderTheMouse(ListboxModeBase):
    """Reveal guarantees VISIBILITY; the hint guarantees POSITION.

    Reported after reveal shipped: on a same-size repaint the content still moved
    under the mouse. A repaint builds a different listbox with cur=0, so the
    reveal lands the selection at the BOTTOM of the window rather than where the
    user clicked. The hint carries the view across.
    """
    SMALL = Bounds(2.0, 10.0, 30.0, 26.0)

    def _slot_of(self, lb, item):
        for i, sec in enumerate(lb.sections or []):
            if sec.item_index is not None and lb._items[sec.item_index] is item:
                return i
        return None

    def _repaint(self, items, hint=None):
        lb = self._lb(items, bounds=self.SMALL, select=True, reveal=True, hint=hint)
        lb._present(FakeEvent())
        return lb

    def test_same_size_repaint_keeps_the_slot(self):
        items = [f"item {i}" for i in range(40)]
        old = self._repaint(items)
        old.cur = 12
        old._present(FakeEvent())
        clicked = old._items[old.sections[1].item_index]     # 2nd visible row
        old.selected = [clicked]
        old._present(FakeEvent())
        slot_before = self._slot_of(old, clicked)
        self.assertIsNotNone(slot_before)

        new = self._repaint(items, hint=old.get_selection_hint())
        self.assertEqual(self._slot_of(new, clicked), slot_before)

    def test_without_the_hint_the_row_moves(self):
        """The complaint, pinned: this is what the hint is for."""
        items = [f"item {i}" for i in range(40)]
        old = self._repaint(items)
        old.cur = 12
        old._present(FakeEvent())
        clicked = old._items[old.sections[1].item_index]
        old.selected = [clicked]
        old._present(FakeEvent())
        slot_before = self._slot_of(old, clicked)

        new = self._repaint(items)                            # no hint
        self.assertNotEqual(self._slot_of(new, clicked), slot_before)

    def test_hint_keeps_it_visible_too(self):
        items = [f"item {i}" for i in range(40)]
        old = self._repaint(items)
        old.cur = 20
        old._present(FakeEvent())
        old.selected = [old._items[old.sections[0].item_index]]
        old._present(FakeEvent())
        new = self._repaint(items, hint=old.get_selection_hint())
        self.assertIn(new._items.index(new.selected[0]), self._shown(new))

    def test_an_explicit_selection_beats_the_hint(self):
        """The caller sets the selection after construction; the hint is applied
        at present time. A stale hint must not override a deliberate choice --
        the gallery's tour moves the selection itself on every step."""
        items = [f"item {i}" for i in range(40)]
        old = self._repaint(items)
        old.set_selected_index(3, False)
        old._present(FakeEvent())
        hint = old.get_selection_hint()

        new = self._lb(items, bounds=self.SMALL, select=True, reveal=True, hint=hint)
        new.set_selected_index(30, False)          # what the caller asked for
        new._present(FakeEvent())
        self.assertEqual(new.unfiltered_items.index(new.selected[0]), 30)
        self.assertIn(30, self._shown(new))        # and revealed

    def test_stale_hint_from_a_shorter_list(self):
        old = self._repaint([f"item {i}" for i in range(40)])
        old.cur = 30
        old.set_selected_index(35, False)
        old._present(FakeEvent())
        new = self._repaint([f"item {i}" for i in range(5)],
                            hint=old.get_selection_hint())
        self.assertLess(new.cur, 5)
        self.assertTrue(self._shown(new))

    def test_garbage_hint_does_not_raise(self):
        items = [f"item {i}" for i in range(40)]
        for junk in (None, "nonsense", 42, {}, {"cur": "x", "selected_index": 999}):
            lb = self._repaint(items, hint=junk)
            self.assertTrue(self._shown(lb))


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
