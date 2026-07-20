import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

from sbs_utils.mast.parsers import LayoutAreaParser, StyleDefinition


class TestLexerUnmatchedChar(unittest.TestCase):
    """An unmatched character must raise, not hang.

    `match = True` used to be set unconditionally inside the rule loop, which
    made the `if not match: raise` branch dead code. A character no rule
    matches left `source` unchanged and `while len(source)>0` spun forever --
    so `row-height: 50%;` hung Cosmos rather than reporting a syntax error.
    """

    def test_percent_raises_instead_of_hanging(self):
        with self.assertRaises(Exception):
            LayoutAreaParser.lex("50%")

    def test_other_unmatched_chars_raise(self):
        for bad in ("#", "@", "50$", "10 & 20"):
            with self.assertRaises(Exception):
                LayoutAreaParser.lex(bad)

    def test_percent_in_a_style_string_raises(self):
        with self.assertRaises(Exception):
            StyleDefinition.parse("col-width: 50%;")


class TestLexerStillAcceptsValidInput(unittest.TestCase):
    """The fix must not change any value that lexes today."""

    def _types(self, source):
        return [t.token_type for t in LayoutAreaParser.lex(source)]

    def test_digits(self):
        self.assertEqual(self._types("50"), ["digits", "eof"])

    def test_pixels(self):
        self.assertEqual(self._types("10px"), ["pixels", "eof"])

    def test_ems(self):
        self.assertEqual(self._types("2.5em"), ["ems", "eof"])

    def test_identifier(self):
        self.assertEqual(self._types("myvar"), ["id", "eof"])

    def test_whitespace_is_dropped(self):
        self.assertEqual(self._types("  50  "), ["digits", "eof"])

    def test_arithmetic(self):
        self.assertEqual(self._types("10+20"), ["digits", "plus", "digits", "eof"])

    def test_min_max_functions(self):
        self.assertEqual(
            self._types("min(10,20)"),
            ["min", "lparen", "digits", "comma", "digits", "rparen", "eof"])

    def test_area_list_still_parses(self):
        parsed = StyleDefinition.parse("area: 0,0,100,50;")
        self.assertEqual(len(parsed["area"]), 4)


if __name__ == "__main__":
    unittest.main()
