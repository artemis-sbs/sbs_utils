"""`col-width: square` — as wide as it is tall.

It joins the keyword family `col-width` already carries (`content`, `min-content`,
`max-content`, `1fr`/`auto`, `fit-content`) rather than being a new boolean style,
because it is the same KIND of thing: a rule for deriving a width. `content` means
"as wide as my content"; `square` means "as wide as I am tall". It is the only one
that reads the other axis, which is why it is a WIDTH rule with no row-height
counterpart.

The rule it enforces matters more than the spelling: an explicit width and `square`
are MUTUALLY EXCLUSIVE. A square column that also carries a width is counted twice
by _resolve_col_widths — in `squares` AND in `assigned_cols`/`assigned_space` — so
the row reserves its space twice over and, since the engine does not clip, draws
the surplus over and outside its neighbours.
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest

from sbs_utils.mast.parsers import (
    StyleDefinition, SQUARE, CONTENT, AUTO, MIN_CONTENT, ContentSize)
from sbs_utils.pages.layout.column import Column, apply_col_width
from sbs_utils.pages.layout.layout import Layout


class TestSquareParses(unittest.TestCase):
    def test_col_width_square_parses_to_the_marker(self):
        self.assertIs(StyleDefinition.parse_width("square"), SQUARE)

    def test_case_and_padding_do_not_matter(self):
        for spelling in (" square", "SQUARE", " Square "):
            self.assertIs(StyleDefinition.parse_width(spelling), SQUARE,
                          spelling)

    def test_it_is_one_of_the_width_keyword_family(self):
        self.assertIsInstance(SQUARE, ContentSize)
        for other in (CONTENT, AUTO, MIN_CONTENT):
            self.assertIsNot(SQUARE, other)
            self.assertNotEqual(SQUARE, other)

    def test_the_other_keywords_still_parse(self):
        # The family is a shared table; adding to it must not disturb it.
        self.assertIs(StyleDefinition.parse_width("content"), CONTENT)
        self.assertIs(StyleDefinition.parse_width("auto"), AUTO)
        self.assertIs(StyleDefinition.parse_width("1fr"), AUTO)
        self.assertIs(StyleDefinition.parse_width("min-content"), MIN_CONTENT)

    def test_ordinary_widths_are_untouched(self):
        # A numeric width parses to an expression AST evaluated later, not to a
        # keyword marker - adding to the family must not capture it.
        w = StyleDefinition.parse_width("25")
        self.assertNotIsInstance(w, ContentSize)
        self.assertIsNotNone(w)

    def test_row_height_square_is_rejected_loudly(self):
        # Not accepted as a no-op: square derives a WIDTH from a height, so a
        # square row-height is circular and the author has the axes swapped.
        with self.assertRaises(Exception) as ctx:
            StyleDefinition.parse_height("square")
        self.assertIn("col-width", str(ctx.exception))

    def test_row_height_keywords_still_work(self):
        self.assertIs(StyleDefinition.parse_height("content"), CONTENT)


class TestSquareAndWidthAreExclusive(unittest.TestCase):
    """The illegal state is deleted, not documented."""

    def test_square_sets_the_flag_and_claims_no_width(self):
        c = Column()
        c.set_col_width(SQUARE)
        self.assertTrue(c.square)
        self.assertIsNone(c.default_width,
                          "a square must not also sit in assigned_space")

    def test_an_explicit_width_un_squares(self):
        c = Column()
        c.square = True                 # e.g. a Face, square from birth
        c.set_col_width(25)
        self.assertFalse(c.square, "the explicit width wins")
        self.assertEqual(c.default_width, 25)

    def test_a_keyword_width_also_un_squares(self):
        c = Column()
        c.square = True
        c.set_col_width(CONTENT)
        self.assertFalse(c.square)
        self.assertIs(c.default_width, CONTENT)

    def test_clearing_the_width_leaves_squareness_alone(self):
        # set_col_width(None) is "no opinion", not "un-square me" — otherwise a
        # style with no col-width would silently un-square every face.
        c = Column()
        c.square = True
        c.set_col_width(None)
        self.assertTrue(c.square)

    def test_a_section_follows_the_same_rule(self):
        # Layout carries `square` too, so a sub-section can be square.
        lay = Layout()
        lay.set_col_width(SQUARE)
        self.assertTrue(lay.square)
        self.assertIsNone(lay.default_width)
        lay.set_col_width(30)
        self.assertFalse(lay.square)

    def test_the_helper_is_the_single_rule(self):
        class _Item:
            square = False
            default_width = None
        it = _Item()
        apply_col_width(it, SQUARE)
        self.assertTrue(it.square)
        apply_col_width(it, 10)
        self.assertFalse(it.square)


class TestSquareThroughAStyleString(unittest.TestCase):
    def test_parsed_from_a_real_style_string(self):
        style = StyleDefinition.parse("col-width: square; padding: 2")
        self.assertIs(style["col-width"], SQUARE)

    def test_applied_to_a_column_from_a_style_string(self):
        style = StyleDefinition.parse("col-width: square")
        c = Column()
        c.set_col_width(style["col-width"])
        self.assertTrue(c.square)
        self.assertIsNone(c.default_width)


if __name__ == "__main__":
    unittest.main()
