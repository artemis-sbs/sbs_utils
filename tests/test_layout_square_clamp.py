"""The square clamp in _resolve_col_widths, and the width it loses.

When square columns would be wider than a normal flex column, the clamp shrinks
squares to the flex width and recomputes the flex width with the now-smaller
squares. The recompute dropped `assigned_space`, so columns with an explicit
col-width stopped being deducted and the flex columns were handed width that
was already spoken for -- the row then sums past 100% and, because the engine
does not clip, draws over whatever is beside it.

Two things make it bite more often than "a square edge case" suggests:

  * square_width is computed unconditionally, so it has a value even in rows
    with NO square columns
  * the clamp is not guarded by `squares > 0`

so a row of three plain columns, one of them fixed, in a tall row, hits it.

TestSquareClampCharacterization documents the behaviour that existed before the
fix (kept as executable history); TestSquareClampFixed asserts the fix.
"""
import types
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

from sbs_utils.helpers import FrameContext
from sbs_utils.vec import Vec3
from sbs_utils.mast.parsers import StyleDefinition

import sbs_utils.procedural.gui  # noqa: F401  (import order: circular via blank)
from sbs_utils.pages.layout.layout import Layout
from sbs_utils.pages.layout.row import Row
from sbs_utils.pages.layout.column import Column


def _col(width=None, square=False):
    c = Column()
    if width is not None:
        c.set_col_width(StyleDefinition.parse(f"col-width: {width};")["col-width"])
    c.square = square
    return c


class _Base(unittest.TestCase):
    def setUp(self):
        FrameContext.aspect_ratios[0] = Vec3(1024, 768, 0)
        FrameContext.context = types.SimpleNamespace(
            sbs=None, sim=None, event=types.SimpleNamespace(client_id=0))

    def tearDown(self):
        FrameContext.context = None

    def widths(self, cols, row_height=None, bottom=100):
        row = Row()
        for c in cols:
            row.add(c)
        if row_height is not None:
            row.set_row_height(
                StyleDefinition.parse(f"row-height: {row_height};")["row-height"])
        sec = Layout("t", [row], 0, 0, 100, bottom)
        sec.calc(0)
        return [c.bounds.width for c in row.columns]

    def clamp_fires(self, cols, row_height=None):
        """True when square_width exceeded the flex width, i.e. the branch the
        bug lived in was taken."""
        row = Row()
        for c in cols:
            row.add(c)
        if row_height is not None:
            row.set_row_height(
                StyleDefinition.parse(f"row-height: {row_height};")["row-height"])
        sec = Layout("t", [row], 0, 0, 100, 100)
        from sbs_utils.pages.layout.bounds import Bounds
        area = Bounds(0, 0, 100, 100 if row_height is None else row_height)
        n = len([c for c in row.columns if not c.is_hidden])
        ar = FrameContext.aspect_ratios[0]
        actual_width = area.width / n * ar.x / 100
        actual_height = area.height * ar.y / 100
        sq = (actual_height if actual_height < actual_width else actual_width)
        square_width = (sq / ar.x) * 100
        _, widths, _, _ = sec._resolve_col_widths(row, area, ar, None)
        return square_width, widths


class TestSquareClampFixed(_Base):
    """After the fix, a row's columns must never claim more than the row."""

    def test_three_cols_one_fixed_tall_row(self):
        # The headline case. 3 columns, one at 60%, a tall row so square_width
        # (~33%) exceeds the flex width (~20%) and the clamp fires. Before the
        # fix the flex columns got 50 each and the row summed to 160%.
        w = self.widths([_col(60), _col(), _col()])
        self.assertAlmostEqual(sum(w), 100.0, places=3)
        self.assertAlmostEqual(w[0], 60.0, places=3)
        self.assertAlmostEqual(w[1], 20.0, places=3)
        self.assertAlmostEqual(w[2], 20.0, places=3)

    def test_no_squares_present_still_correct(self):
        # Nothing here is square; the clamp must not silently redistribute.
        for fixed in (40, 60, 75):
            w = self.widths([_col(fixed), _col(), _col()])
            self.assertAlmostEqual(sum(w), 100.0, places=3,
                                   msg=f"fixed={fixed} overflows: {w}")

    def test_with_a_real_square(self):
        w = self.widths([_col(50), _col(square=True), _col()])
        self.assertLessEqual(sum(w), 100.0 + 1e-6, f"overflows: {w}")

    def test_two_fixed_one_flex(self):
        w = self.widths([_col(35), _col(35), _col()])
        self.assertAlmostEqual(sum(w), 100.0, places=3)
        self.assertAlmostEqual(w[2], 30.0, places=3)

    def test_short_row_does_not_trigger_clamp(self):
        # A short row makes square_width small, so the clamp branch is skipped
        # entirely. This was correct before the fix too -- pinned so the fix
        # cannot regress the non-clamp path.
        w = self.widths([_col(60), _col(), _col()], row_height=5)
        self.assertAlmostEqual(sum(w), 100.0, places=3)

    def test_all_flex_unaffected(self):
        w = self.widths([_col(), _col(), _col()])
        for x in w:
            self.assertAlmostEqual(x, 100.0 / 3.0, places=3)

    def test_fixed_widths_are_honoured_exactly(self):
        w = self.widths([_col(60), _col(), _col()])
        self.assertAlmostEqual(w[0], 60.0, places=3)

    def test_oversubscribed_fixed_does_not_gain_width(self):
        # Fixed columns already exceeding the row is a pre-existing authoring
        # error; the flex column should get 0, not be handed phantom space.
        w = self.widths([_col(70), _col(70), _col()])
        self.assertGreaterEqual(w[2], 0.0)
        self.assertLessEqual(w[2], 1e-6, f"flex column gained width: {w}")


class TestSquareClampCharacterization(_Base):
    """Executable record of WHY the clamp exists, so the fix does not remove it.

    Squares must still be shrunk to the flex width when they would otherwise
    dominate the row -- that behaviour is intended and stays.
    """

    def test_square_is_shrunk_when_it_would_dominate(self):
        # One square + one flex in a tall row: the square would be ~50% wide by
        # the aspect calculation; it must not exceed what a flex column gets.
        w = self.widths([_col(square=True), _col()])
        self.assertLessEqual(sum(w), 100.0 + 1e-6)
        self.assertLessEqual(w[0], 50.0 + 1e-6)

    def test_all_squares_row_still_uses_square_width(self):
        w = self.widths([_col(square=True), _col(square=True)])
        self.assertAlmostEqual(w[0], w[1], places=6)
        self.assertLessEqual(sum(w), 100.0 + 1e-6)


if __name__ == "__main__":
    unittest.main()
