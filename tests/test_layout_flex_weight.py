"""Weighted flex: `2fr` means two shares, the way CSS grid means it.

`1fr` used to be a whole KEYWORD - the lexer matched those three characters and
nothing else. So `2fr` was not an unsupported ratio, it was not a ratio at all: it
fell through to the numeric rule as the number 2 with a dangling `fr`, and a bare
number is a PERCENTAGE. `row-height: 2fr` asked for 2% of the screen, about 15px at
720p, with no error and no warning.

That shipped on the xESS choice list, where the rows were laid out at y=99.6..103.5 -
below the bottom edge - and was reported as "the buttons are at the bottom and less
than 20 pixels", which is what 2% looks like from a chair.

THE POINT OF THESE TESTS IS THE PAIR:

* a weight does what it says (`2fr` is twice `1fr`), and
* EVERY LAYOUT THAT DOES NOT USE ONE IS UNMOVED - an even split IS a weighted split
  when every weight is 1. `test_layout_geometry_golden` pins that across a corpus;
  these pin the arithmetic directly so a failure says which rule broke.
"""
import unittest

from sbs_utils.fs import test_set_exe_dir

test_set_exe_dir()

from sbs_utils.mast.parsers import (AUTO, ContentSize, StyleDefinition,
                                    flex_weight)


class TheParserUnderstandsAWeight(unittest.TestCase):
    def test_a_plain_number_of_shares(self):
        self.assertEqual(2.0, StyleDefinition.parse_height("2fr").weight)
        self.assertEqual(10.0, StyleDefinition.parse_height("10fr").weight)

    def test_a_fraction_of_a_share(self):
        """`0.5fr` is half of `1fr`, so two of them equal one - CSS allows it and
        there is no reason to be stricter than the thing being copied."""
        self.assertEqual(0.5, StyleDefinition.parse_height("0.5fr").weight)

    def test_it_is_still_the_flex_MODE(self):
        """A weight changes the SHARE, not the kind of size. `2fr` must stay in the
        flex pool and keep its min-content floor, or LM issue 672 comes back for
        every weighted row."""
        two = StyleDefinition.parse_height("2fr")
        self.assertTrue(two.is_auto)
        self.assertEqual("1fr", two.mode)

    def test_1fr_and_auto_are_still_the_INTERNED_instance(self):
        """The layout hot path compares these by IDENTITY. If `1fr` started
        allocating a new ContentSize per parse, every `raw_width is AUTO` test in
        the engine would quietly stop matching - a far worse bug than the one this
        feature fixes, and a silent one."""
        self.assertIs(AUTO, StyleDefinition.parse_height("1fr"))
        self.assertIs(AUTO, StyleDefinition.parse_height("auto"))
        self.assertIs(AUTO, StyleDefinition.parse_width("1fr"))

    def test_a_weight_of_one_equals_plain_flex(self):
        self.assertEqual(AUTO, StyleDefinition.parse_height("1.0fr"))

    def test_zero_shares_is_REFUSED(self):
        """CSS gives a `0fr` item none of the leftover space. Here that is a row of
        no height that STILL DRAWS ITS TEXT, over whatever is above it - the engine
        does not clip. That is the exact shape of LM issue 672 and it is not worth
        reintroducing for a spelling nobody needs."""
        with self.assertRaises(Exception):
            StyleDefinition.parse_height("0fr")

    def test_it_is_not_confused_with_a_bare_number(self):
        """The whole bug: `2fr` must never again parse as the number 2."""
        two_fr = StyleDefinition.parse_height("2fr")
        self.assertIsInstance(two_fr, ContentSize)

    def test_an_identifier_that_merely_ENDS_in_fr_is_not_one(self):
        self.assertIsNone(StyleDefinition._content_size("frfr"))

    def test_the_weight_is_part_of_equality(self):
        """These are cached and compared; two different shares must not be equal or
        a re-layout would reuse the wrong one."""
        self.assertNotEqual(StyleDefinition.parse_height("2fr"),
                            StyleDefinition.parse_height("3fr"))
        self.assertEqual(StyleDefinition.parse_height("2fr"),
                         StyleDefinition.parse_height("2fr"))

    def test_it_reads_back_the_way_it_was_written(self):
        self.assertEqual("ContentSize(2fr)",
                         repr(StyleDefinition.parse_height("2fr")))
        self.assertEqual("ContentSize(1fr)", repr(AUTO))

    def test_everything_else_weighs_one(self):
        for spell in ("content", "min-content", "max-content", "auto", "1fr"):
            self.assertEqual(1.0, flex_weight(StyleDefinition.parse_height(spell)),
                             spell)


class TheRowsDivideByShare(unittest.TestCase):
    """Measured on real rows, through `Layout.calc`, rather than on the numbers that
    feed it - the arithmetic is only interesting if it reaches the rects."""

    def _heights(self, *spec):
        """Lay out one section of rows with these `row-height` values and return the
        height each row actually got, in screen percent.

        Driven the way `layout_corpus` drives it - `sec.calc(0)` with the aspect
        ratio in `FrameContext` - because that is the harness the golden test has
        already proved builds a real layout.
        """
        from sbs_utils.helpers import FrameContext
        from sbs_utils.pages.layout.layout import Layout
        from sbs_utils.pages.layout.row import Row
        from sbs_utils.pages.layout.column import Column
        from sbs_utils.vec import Vec3

        FrameContext.aspect_ratios[0] = Vec3(1920, 1080, 0)
        rows = []
        for value in spec:
            row = Row()
            row.add(Column())
            if value is not None:
                row.set_row_height(
                    StyleDefinition.parse("row-height: %s;" % value)["row-height"])
            rows.append(row)
        sec = Layout("weights", rows, 0, 0, 100, 100)
        sec.calc(0)
        return [round(r.height, 4) for r in sec.rows]

    def test_two_plain_rows_still_split_evenly(self):
        a, b = self._heights("1fr", "1fr")
        self.assertAlmostEqual(a, b, places=3)
        self.assertAlmostEqual(50.0, a, places=3)

    def test_a_2fr_row_is_twice_a_1fr_row(self):
        one, two = self._heights("1fr", "2fr")
        self.assertAlmostEqual(2.0, two / one, places=3)

    def test_and_they_still_fill_the_section(self):
        """The share is the leftover divided by the TOTAL weight, so the rows must
        add up to the whole section however they are weighted."""
        self.assertAlmostEqual(100.0, sum(self._heights("1fr", "2fr")), places=3)
        self.assertAlmostEqual(100.0, sum(self._heights("1fr", "2fr", "3fr")),
                               places=3)

    def test_the_shares_are_the_ratio_asked_for(self):
        one, two, three = self._heights("1fr", "2fr", "3fr")
        self.assertAlmostEqual(100.0 / 6, one, places=3)
        self.assertAlmostEqual(200.0 / 6, two, places=3)
        self.assertAlmostEqual(300.0 / 6, three, places=3)

    def test_a_fixed_row_is_taken_out_FIRST(self):
        """Weights divide what is left after the fixed rows, exactly as CSS does -
        otherwise a weighted row would eat into a row that asked for a real size."""
        fixed, one, two = self._heights("40", "1fr", "2fr")
        self.assertAlmostEqual(40.0, fixed, places=3)
        self.assertAlmostEqual(20.0, one, places=3)
        self.assertAlmostEqual(40.0, two, places=3)

    def test_an_unstyled_row_weighs_one(self):
        """Most rows in the codebase say nothing at all. They have to keep dividing
        evenly among themselves and against an explicit `1fr`."""
        a, b = self._heights(None, "1fr")
        self.assertAlmostEqual(a, b, places=3)

    def test_a_weighted_row_still_has_a_min_content_FLOOR(self):
        """`2fr` is the flex MODE with a bigger share, so it keeps everything `1fr`
        has. Losing the floor here would bring LM issue 672 back for exactly the
        rows an author cared enough about to weight."""
        two = StyleDefinition.parse_height("2fr")
        self.assertTrue(two.is_auto)

    def test_a_half_share(self):
        half, one = self._heights("0.5fr", "1fr")
        self.assertAlmostEqual(2.0, one / half, places=3)


class TheColumnsDivideByShareToo(unittest.TestCase):
    """The same unit on the other axis.

    Doing rows only would leave `col-width: 2fr` still meaning 2% - the identical
    silent bug, one axis over, now with the feature's own documentation implying it
    works. A half-implemented unit is worse than none.
    """

    def _widths(self, *spec):
        from sbs_utils.helpers import FrameContext
        from sbs_utils.pages.layout.layout import Layout
        from sbs_utils.pages.layout.row import Row
        from sbs_utils.pages.layout.column import Column
        from sbs_utils.vec import Vec3

        FrameContext.aspect_ratios[0] = Vec3(1920, 1080, 0)
        row = Row()
        for value in spec:
            col = Column()
            if value is not None:
                col.set_col_width(
                    StyleDefinition.parse("col-width: %s;" % value)["col-width"])
            row.add(col)
        sec = Layout("colweights", [row], 0, 0, 100, 100)
        sec.calc(0)
        return [round(c.bounds.right - c.bounds.left, 4) for c in sec.rows[0].columns]

    def test_two_plain_columns_still_split_evenly(self):
        a, b = self._widths("1fr", "1fr")
        self.assertAlmostEqual(a, b, places=3)

    def test_a_2fr_column_is_twice_a_1fr_column(self):
        one, two = self._widths("1fr", "2fr")
        self.assertAlmostEqual(2.0, two / one, places=3)

    def test_and_they_still_fill_the_row(self):
        self.assertAlmostEqual(100.0, sum(self._widths("1fr", "2fr")), places=2)

    def test_a_fixed_column_is_taken_out_first(self):
        fixed, one, two = self._widths("40", "1fr", "2fr")
        self.assertAlmostEqual(40.0, fixed, places=2)
        self.assertAlmostEqual(2.0, two / one, places=3)

    def test_an_unstyled_column_weighs_one(self):
        a, b = self._widths(None, "1fr")
        self.assertAlmostEqual(a, b, places=3)


if __name__ == "__main__":
    unittest.main()
