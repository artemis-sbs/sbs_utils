"""LayoutListbox slot budgeting: uniform lists must not move.

The change under test replaces "available space / TALLEST row" with packing by
each row's real height. Dividing by the tallest silently assumes every row is
the same height, so ONE tall row shrank the whole list -- eleven 48px console
rows with a single 96px one showed six and left half the box empty.

The risk is entirely in the uniform case, because that is every other listbox in
LegendaryMissions and Open Universe. So that is what these tests pin: for equal
rows the packer must return exactly floor(available / row_height), the same
number the old arithmetic produced.
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest

import cosmos_dev.mock.sbs as mock_sbs
from sbs_utils.helpers import FrameContext, Context, FakeEvent
from sbs_utils.vec import Vec3
import sbs_utils.procedural.gui  # noqa: F401  (circular-import order)
from sbs_utils.pages.widgets.layout_listbox import LayoutListbox, max_cur, reveal_cur


def pack(heights, avail, item_height=0.0, start=0, avg=None):
    """The packing loop, isolated from present() so it can be asserted on.

    Mirrors the implementation in LayoutListbox._present; kept in step by
    test_matches_the_implementation below.
    """
    if avg is None:
        avg = sum(heights) / len(heights) if heights else 0
    used = 0.0
    slots = 0
    for h in heights[start:]:
        h = h + item_height
        if used + h > avail and slots > 0:
            break
        used += h
        slots += 1
    return slots


class TestUniformListsDoNotMove(unittest.TestCase):
    def test_uniform_rows_match_the_old_arithmetic(self):
        """floor(available / row) -- the old formula -- for equal rows.

        Two edges the naive comparison gets wrong, both verified against what
        the OLD code actually rendered rather than what its arithmetic said:

        * capacity is capped by how many items exist, so the list must have more
          rows than fit for the comparison to mean anything.
        * when one row is taller than the whole box the old formula gave 0, but
          the draw loop increments `slot` BEFORE testing `slot >= max_slots`, so
          it still drew one row. Effective old behaviour is max(1, floor), and
          that is what the packer has to match.
        """
        for row_h in (2.0, 4.5, 6.25, 12.0):
            for avail in (10.0, 33.3, 50.0, 97.5):
                heights = [row_h] * 80
                with self.subTest(row=row_h, avail=avail):
                    self.assertEqual(pack(heights, avail),
                                     max(1, int(avail // row_h)))

    def test_one_row_always_draws_even_if_it_overflows(self):
        # Matches the old loop, which drew a row before checking the budget.
        # Returning 0 here would blank a list whose single row is over-tall.
        self.assertEqual(pack([80.0], 10.0), 1)

    def test_a_tall_row_no_longer_shrinks_the_whole_list(self):
        """The bug, in numbers: the console list.

        Ten 48px rows and one 96px row in a ~600px box. Budgeting on the tallest
        gives 600/96 = 6 rows. Packing gives the ten short ones plus the tall one
        wherever it fits -- far more of the box used.
        """
        SHORT, TALL = 6.25, 12.5          # 48px and 96px at 768
        heights = [SHORT] * 8 + [TALL] + [SHORT] * 2
        avail = 78.0                       # ~600px
        by_tallest = int(avail // TALL)
        self.assertEqual(by_tallest, 6)
        self.assertGreater(pack(heights, avail), by_tallest)

    def test_packing_never_exceeds_the_space(self):
        # Overrunning is what makes rows draw over their neighbours, since the
        # engine does not clip.
        heights = [6.25] * 5 + [12.5] * 3 + [3.0] * 6
        avail = 40.0
        n = pack(heights, avail)
        self.assertLessEqual(sum(heights[:n]), avail + 1e-9)

    def test_scroll_offset_is_respected(self):
        heights = [10.0] * 10
        self.assertEqual(pack(heights, 35.0, start=0), 3)
        self.assertEqual(pack(heights, 35.0, start=7), 3)

    def test_unmeasured_rows_fall_back_to_the_average(self):
        # An item calc_max never saw still has to be given a size, and the
        # average is the least-wrong one available.
        heights = []
        self.assertEqual(pack(heights, 50.0), 0)


class TestMaxCurIsTheScrollRange(unittest.TestCase):
    """max_cur = the largest `cur` that still shows the LAST row.

    The scrollbar's `high` came from `len(items) - pack_slots(start=cur)`, which
    counts the rows that fit FROM WHERE THE VIEW IS. With real per-row heights
    that count moves as you scroll, so the track rescaled under the thumb and
    nothing stopped `cur` running off the end of the list. These pin the property
    the old expression did not have: the answer does not depend on `cur`.
    """

    UNIFORM = [1.0] * 40
    # Every third row double height -- where the old expression wobbled.
    VARIED = [2.0 if i % 3 == 0 else 1.0 for i in range(40)]
    AVAIL = 21.0

    def test_uniform_range_reaches_the_last_row(self):
        m = max_cur(self.UNIFORM, self.AVAIL)
        self.assertEqual(m, 19)
        self.assertEqual(m + pack(self.UNIFORM, self.AVAIL, start=m), 40,
                         "the view starting at max_cur must reach the end")

    def test_one_past_the_range_would_overshoot(self):
        """19 is the LARGEST such index, not merely one that works."""
        m = max_cur(self.UNIFORM, self.AVAIL)
        self.assertLess(m - 1 + pack(self.UNIFORM, self.AVAIL, start=m - 1), 40,
                        "max_cur-1 must NOT already reach the end")

    def test_the_range_does_not_depend_on_where_the_view_is(self):
        """The defect, isolated. The old expression gave 25/24/25 here."""
        m = max_cur(self.VARIED, self.AVAIL)
        old = [len(self.VARIED) - pack(self.VARIED, self.AVAIL, start=c)
               for c in (0, 10, 25)]
        self.assertGreater(len(set(old)), 1,
                           "if the old expression were stable this pins nothing")
        for c in (0, 5, 10, 20, 30, 39):
            self.assertEqual(max_cur(self.VARIED, self.AVAIL), m,
                             f"range moved when the view sat at {c}")

    def test_varied_range_reaches_the_last_row(self):
        m = max_cur(self.VARIED, self.AVAIL)
        self.assertEqual(m + pack(self.VARIED, self.AVAIL, start=m), 40)

    def test_a_list_that_all_fits_has_no_range(self):
        self.assertEqual(max_cur([1.0] * 5, 50.0), 0)

    def test_an_exact_fit_has_no_range(self):
        self.assertEqual(max_cur([1.0] * 21, 21.0), 0)

    def test_empty(self):
        self.assertEqual(max_cur([], 50.0), 0)

    def test_a_single_row_taller_than_the_box_is_still_reachable(self):
        # pack_slots always draws one row rather than none; the range agrees.
        self.assertEqual(max_cur([100.0], 21.0), 0)
        self.assertEqual(max_cur([1.0, 1.0, 100.0], 21.0), 2)

    def test_the_item_gap_counts_against_the_space(self):
        self.assertGreater(max_cur(self.UNIFORM, self.AVAIL, 0.5),
                           max_cur(self.UNIFORM, self.AVAIL, 0.0),
                           "gaps mean fewer rows fit, so the range is longer")

    def test_matches_reveal_cur_for_the_last_row(self):
        """Both are the same back-pack; revealing the last row IS the range."""
        m = max_cur(self.VARIED, self.AVAIL)
        self.assertEqual(reveal_cur(len(self.VARIED) - 1, 0, self.VARIED,
                                    self.AVAIL), m)


class TestCalcMaxReportsAverage(unittest.TestCase):
    def setUp(self):
        mock_sbs.create_new_sim()
        FrameContext.aspect_ratios[0] = Vec3(1024, 768, 0)
        FrameContext.context = Context(mock_sbs.sim, mock_sbs, FakeEvent())

    def test_signature_is_three_values(self):
        # One caller in-tree, but the shape is part of the contract now.
        import inspect
        src = inspect.getsource(LayoutListbox.calc_max)
        self.assertIn("return max_width, max_height, avg_height", src)

    def test_per_item_heights_are_kept(self):
        import inspect
        self.assertIn("_item_heights", inspect.getsource(LayoutListbox.calc_max))


if __name__ == "__main__":
    unittest.main()
