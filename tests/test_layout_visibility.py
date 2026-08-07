"""Visibility is two independent flags, and only one of them belongs to the script.

``_show`` is what the script asked for (``show()`` / ``gui_show`` / ``gui_hide``).
``_is_shown`` is what the parent computed this frame from bounds containment.
``is_hidden`` is the OR of the two, and ``bounds`` reports the sentinel
``Bounds.hidden`` only while a present pass is running -- layout math outside a
present must see real geometry or a hidden element can never be measured back
into place.

Row, Column and Layout each carry their own copy of these semantics, so the
truth table is asserted against all three: they will drift otherwise. (Row
already spells its `is_hidden` clauses in the opposite order from Column.)
"""
import types
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

from sbs_utils.helpers import FrameContext
from sbs_utils.vec import Vec3

# procedural.gui must be imported before pages.layout.layout -- circular via blank
import sbs_utils.procedural.gui  # noqa: F401
from sbs_utils.pages.layout.bounds import Bounds
from sbs_utils.pages.layout.column import Column
from sbs_utils.pages.layout.layout import Layout
from sbs_utils.pages.layout.row import Row
from sbs_utils.procedural.gui.update import gui_hide, gui_show


class FakeSbs:
    def __getattr__(self, name):
        return lambda *a, **k: None


class FakeEvent:
    client_id = 0


class _Base(unittest.TestCase):
    def setUp(self):
        FrameContext.aspect_ratios[0] = Vec3(1000, 1000, 0)
        FrameContext.context = types.SimpleNamespace(
            sbs=FakeSbs(), sim=None, event=FakeEvent())

    def tearDown(self):
        FrameContext.context = None


def make(kind):
    """A bare item of each kind, with the same starting visibility."""
    return {Row: Row, Column: Column, Layout: Layout}[kind]()


KINDS = (Row, Column, Layout)


class TestTwoFlagTruthTable(_Base):
    """is_hidden is the OR of the two flags, on every layout class."""

    def test_a_fresh_item_is_visible(self):
        for kind in KINDS:
            with self.subTest(kind=kind.__name__):
                self.assertFalse(make(kind).is_hidden)

    def test_the_script_flag_alone_hides(self):
        for kind in KINDS:
            with self.subTest(kind=kind.__name__):
                item = make(kind)
                item.show(False)
                self.assertTrue(item.is_hidden)

    def test_the_parent_flag_alone_hides(self):
        """Clipped by the parent, even though the script wants it shown."""
        for kind in KINDS:
            with self.subTest(kind=kind.__name__):
                item = make(kind)
                item._is_shown = False
                self.assertTrue(item.is_hidden)
                self.assertTrue(item._show, "the script's intent is untouched")

    def test_both_flags_down_hides(self):
        for kind in KINDS:
            with self.subTest(kind=kind.__name__):
                item = make(kind)
                item.show(False)
                item._is_shown = False
                self.assertTrue(item.is_hidden)

    def test_showing_again_restores(self):
        for kind in KINDS:
            with self.subTest(kind=kind.__name__):
                item = make(kind)
                item.show(False)
                item.show(True)
                self.assertFalse(item.is_hidden)

    def test_the_parent_flag_still_wins_after_show(self):
        """show(True) cannot override clipping -- that is the parent's call."""
        for kind in KINDS:
            with self.subTest(kind=kind.__name__):
                item = make(kind)
                item._is_shown = False
                item.show(True)
                self.assertTrue(item.is_hidden)


class TestShowIsIdempotent(_Base):
    """show() with the value it already has must not dirty the layout.

    A repaint loop that calls gui_show() every frame would otherwise mark the
    layout dirty every frame and never settle.
    """

    def _count_dirty(self, item, attr):
        calls = []
        setattr(item, attr, lambda *a, **k: calls.append(1))
        return calls

    def test_setting_the_same_value_twice_dirties_once(self):
        for kind, attr in ((Row, "mark_layout_dirty"),
                           (Column, "mark_layout_dirty"),
                           (Layout, "mark_visual_dirty")):
            with self.subTest(kind=kind.__name__):
                item = make(kind)
                calls = self._count_dirty(item, attr)
                item.show(False)
                item.show(False)
                item.show(False)
                self.assertEqual(1, len(calls))

    def test_showing_an_already_visible_item_does_nothing(self):
        for kind, attr in ((Row, "mark_layout_dirty"),
                           (Column, "mark_layout_dirty"),
                           (Layout, "mark_visual_dirty")):
            with self.subTest(kind=kind.__name__):
                item = make(kind)
                calls = self._count_dirty(item, attr)
                item.show(True)                  # already True
                self.assertEqual(0, len(calls))

    def test_a_real_change_still_dirties(self):
        for kind, attr in ((Row, "mark_layout_dirty"),
                           (Column, "mark_layout_dirty"),
                           (Layout, "mark_visual_dirty")):
            with self.subTest(kind=kind.__name__):
                item = make(kind)
                calls = self._count_dirty(item, attr)
                item.show(False)
                item.show(True)
                self.assertEqual(2, len(calls))


class TestBoundsOnlyHideWhilePresenting(_Base):
    """Outside a present pass, bounds are real even for a hidden item.

    This is the change that lets a hidden element be measured and laid out
    normally; only the present pass substitutes the off-screen sentinel so the
    engine draws it nowhere.
    """

    REAL = (10, 20, 30, 40)

    def _item(self, kind):
        item = make(kind)
        # the bounds property setter, not set_bounds() -- Row does not have one
        item.bounds = Bounds(*self.REAL)
        return item

    def _tuple(self, b):
        return (b.left, b.top, b.right, b.bottom)

    def test_visible_and_not_presenting_gives_real_bounds(self):
        for kind in KINDS:
            with self.subTest(kind=kind.__name__):
                self.assertEqual(self.REAL, self._tuple(self._item(kind).bounds))

    def test_hidden_and_not_presenting_still_gives_real_bounds(self):
        for kind in KINDS:
            with self.subTest(kind=kind.__name__):
                item = self._item(kind)
                item.show(False)
                self.assertEqual(self.REAL, self._tuple(item.bounds),
                                 "layout math outside present must see real geometry")

    def test_visible_and_presenting_gives_real_bounds(self):
        for kind in KINDS:
            with self.subTest(kind=kind.__name__):
                item = self._item(kind)
                item.is_presenting = True
                self.assertEqual(self.REAL, self._tuple(item.bounds))

    def test_hidden_and_presenting_gives_the_sentinel(self):
        for kind in KINDS:
            with self.subTest(kind=kind.__name__):
                item = self._item(kind)
                item.show(False)
                item.is_presenting = True
                self.assertEqual((-1011, -1011, -999, -999),
                                 self._tuple(item.bounds))

    def test_clipped_and_presenting_gives_the_sentinel(self):
        for kind in KINDS:
            with self.subTest(kind=kind.__name__):
                item = self._item(kind)
                item._is_shown = False
                item.is_presenting = True
                self.assertEqual((-1011, -1011, -999, -999),
                                 self._tuple(item.bounds))


class TestPresentingFlagIsAlwaysCleared(_Base):
    """A raise mid-present must not leave is_presenting set.

    If it stays set, `bounds` keeps handing out Bounds.hidden forever and every
    later layout pass computes against off-screen coordinates.
    """

    def test_column(self):
        class Boom(Column):
            def _present(self, event):
                raise RuntimeError("boom")
        col = Boom()
        with self.assertRaises(RuntimeError):
            col.present(FakeEvent())
        self.assertFalse(col.is_presenting)

    def test_row(self):
        class Boom(Column):
            def _present(self, event):
                raise RuntimeError("boom")
        row = Row()
        row.add(Boom())
        with self.assertRaises(RuntimeError):
            row.present(FakeEvent())
        self.assertFalse(row.is_presenting)

    def test_layout(self):
        class Boom(Layout):
            def _present(self, event):
                raise RuntimeError("boom")
        sec = Boom("t", [Row()], 0, 0, 100, 100)
        with self.assertRaises(RuntimeError):
            sec.present(FakeEvent())
        self.assertFalse(sec.is_presenting)

    def test_bounds_are_trustworthy_after_the_raise(self):
        class Boom(Column):
            def _present(self, event):
                raise RuntimeError("boom")
        col = Boom()
        col.set_bounds(Bounds(10, 20, 30, 40))
        col.show(False)
        with self.assertRaises(RuntimeError):
            col.present(FakeEvent())
        b = col.bounds
        self.assertEqual((10, 20, 30, 40), (b.left, b.top, b.right, b.bottom))


class RecordingColumn(Column):
    """Records that it was presented, so 'still presented while hidden' is testable."""

    def __init__(self):
        super().__init__()
        self.presented = 0

    def _present(self, event):
        self.presented += 1


class TestParentDrivesChildVisibility(_Base):
    """The parent computes _is_shown from containment -- but still presents.

    Skipping the present of an out-of-bounds child is what leaves ghost widgets
    on screen: the engine keeps drawing whatever was last sent for that tag.
    Hiding is done by sending the sentinel bounds, not by staying silent.
    """

    def _row_with(self, col_bounds, row_bounds=(0, 0, 100, 10)):
        """A row presented directly.

        Row.present() does not re-run calc(), so hand-placed bounds survive --
        Layout.present() would immediately lay the column out again.
        """
        col = RecordingColumn()
        col.bounds = Bounds(*col_bounds)
        row = Row()
        row.bounds = Bounds(*row_bounds)
        row.add(col)
        return row, col

    def test_a_contained_child_stays_shown(self):
        row, col = self._row_with((10, 2, 20, 8))
        row.present(FakeEvent())
        self.assertTrue(col._is_shown)
        self.assertFalse(col.is_hidden)

    def test_a_child_outside_its_row_is_marked_not_shown(self):
        row, col = self._row_with((5000, 5000, 6000, 6000))
        row.present(FakeEvent())
        self.assertFalse(col._is_shown)
        self.assertTrue(col.is_hidden)

    def test_an_out_of_bounds_child_is_still_presented(self):
        row, col = self._row_with((5000, 5000, 6000, 6000))
        row.present(FakeEvent())
        self.assertGreater(col.presented, 0,
                           "a clipped child must still be presented, or the "
                           "engine keeps drawing its previous frame (ghost)")

    def test_the_parents_verdict_does_not_touch_the_scripts_intent(self):
        row, col = self._row_with((5000, 5000, 6000, 6000))
        row.present(FakeEvent())
        self.assertTrue(col._show,
                        "clipping is the parent's business; _show is the script's")

    def test_a_hidden_row_forces_its_columns_not_shown(self):
        row, col = self._row_with((10, 2, 20, 8))
        row.show(False)
        row.present(FakeEvent())
        self.assertFalse(col._is_shown)

    def test_a_hidden_row_still_presents_its_columns(self):
        row, col = self._row_with((10, 2, 20, 8))
        row.show(False)
        row.present(FakeEvent())
        self.assertGreater(col.presented, 0)

    def test_a_hidden_layout_forces_its_rows_not_shown(self):
        row, col = self._row_with((10, 2, 20, 8))
        sec = Layout("t", [row], 0, 0, 100, 100)
        sec.show(False)
        sec.present(FakeEvent())
        self.assertFalse(row._is_shown)

    def test_a_visible_layout_leaves_its_rows_shown(self):
        row, col = self._row_with((10, 2, 20, 8))
        sec = Layout("t", [row], 0, 0, 100, 100)
        sec.present(FakeEvent())
        self.assertTrue(row._is_shown)

    def test_a_row_outside_the_layout_is_marked_not_shown(self):
        """Driven through _present so calc() does not re-place the row."""
        row, col = self._row_with((10, 2, 20, 8), row_bounds=(5000, 5000, 6000, 6000))
        sec = Layout("t", [row], 0, 0, 100, 100)
        sec.bounds = Bounds(0, 0, 100, 100)
        sec.is_presenting = True
        try:
            sec._present(FakeEvent())
        finally:
            sec.is_presenting = False
        self.assertFalse(row._is_shown)


class TestHiddenRowsAreNotLaidOut(_Base):
    """A hidden row takes no space -- the visible rows absorb it."""

    def _rows(self, n):
        return [Row() for _ in range(n)]

    def test_hiding_a_row_gives_its_space_to_the_others(self):
        rows = self._rows(2)
        sec = Layout("t", rows, 0, 0, 100, 100)
        sec.calc(0)
        self.assertAlmostEqual(50.0, rows[0].height, places=3)

        rows[1].show(False)
        sec.calc(0)
        self.assertAlmostEqual(100.0, rows[0].height, places=3,
                               msg="a hidden row must not reserve layout space")

    def test_showing_it_again_gives_the_space_back(self):
        rows = self._rows(2)
        sec = Layout("t", rows, 0, 0, 100, 100)
        rows[1].show(False)
        sec.calc(0)
        rows[1].show(True)
        sec.calc(0)
        self.assertAlmostEqual(50.0, rows[0].height, places=3)


class TestRowGeometryExistsFromBirth(_Base):
    """A row hidden before it was ever laid out still has its side attributes.

    calc() writes left/top/right/bottom/width/height every pass, but it also
    filters hidden rows out -- so a row hidden before its first layout pass
    would never receive them. tests/layout_corpus.py reads exactly these, and
    is_out_of_bounds() falls back to them when .bounds is None.
    """

    SIDES = ("left", "top", "right", "bottom", "width", "height")

    def test_a_fresh_row_has_them(self):
        row = Row()
        for name in self.SIDES:
            with self.subTest(attr=name):
                self.assertIsNotNone(getattr(row, name, None))

    def test_they_agree_with_the_constructor(self):
        row = Row(width=30, height=12)
        self.assertEqual(30, row.width)
        self.assertEqual(12, row.height)
        self.assertEqual(30, row.right)
        self.assertEqual(12, row.bottom)

    def test_a_row_hidden_before_its_first_layout_still_has_them(self):
        row = Row()
        row.show(False)
        sec = Layout("t", [row], 0, 0, 100, 100)
        sec.calc(0)                       # the hidden row is filtered out
        for name in self.SIDES:
            with self.subTest(attr=name):
                getattr(row, name)        # must not raise AttributeError

    def test_the_corpus_readout_works_on_a_hidden_row(self):
        """The exact expression tests/layout_corpus.py formats."""
        row = Row()
        row.show(False)
        sec = Layout("t", [row], 0, 0, 100, 100)
        sec.calc(0)
        f"l={row.left:.4f} t={row.top:.4f} w={row.width:.4f} h={row.height:.4f}"


class TestGuiShowAndHide(_Base):
    """gui_hide must record intent even when the item is already off screen.

    The early-return these functions used to have tested `is_hidden`, which is
    true for a merely CLIPPED item. So gui_hide() on a row scrolled out of view
    was a no-op, _show stayed True, and the row popped back into view the moment
    the parent scrolled it back -- the script's hide silently lost.
    """

    def test_hiding_a_clipped_item_records_the_intent(self):
        col = Column()
        col._is_shown = False                 # clipped by the parent right now
        self.assertTrue(col.is_hidden)

        gui_hide(col)
        self.assertFalse(col._show)

        col._is_shown = True                  # parent scrolls it back into view
        self.assertTrue(col.is_hidden, "the script asked for hidden; it must stay hidden")

    def test_showing_a_clipped_item_records_the_intent(self):
        col = Column()
        col.show(False)
        col._is_shown = False
        gui_show(col)
        self.assertTrue(col._show)
        col._is_shown = True
        self.assertFalse(col.is_hidden)

    def test_hiding_a_visible_item(self):
        for kind in KINDS:
            with self.subTest(kind=kind.__name__):
                item = make(kind)
                gui_hide(item)
                self.assertTrue(item.is_hidden)

    def test_showing_a_hidden_item(self):
        for kind in KINDS:
            with self.subTest(kind=kind.__name__):
                item = make(kind)
                gui_hide(item)
                gui_show(item)
                self.assertFalse(item.is_hidden)

    def test_none_is_tolerated(self):
        gui_show(None)
        gui_hide(None)


if __name__ == "__main__":
    unittest.main()
