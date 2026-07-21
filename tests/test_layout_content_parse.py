"""Parsing for the content-size keywords.

`row-height: content;` used to be lexed as a bare identifier, and an unknown
identifier evaluates to 1 -- so it silently produced a 1%-tall row rather than
an error. `min-content`/`max-content` were worse: `min`/`max` are unanchored
lexer rules, so they matched the prefix and parse_func then rejected the
leftover `-content` with "Invalid syntax on token minus".

These tests pin the new behaviour AND, just as importantly, that every existing
size expression still parses to exactly what it did before.
"""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

from sbs_utils.mast.parsers import (
    ContentSize, CONTENT, MIN_CONTENT, MAX_CONTENT,
    LayoutAreaParser, StyleDefinition,
)


def style(text):
    return StyleDefinition.parse(text)


class TestContentKeywords(unittest.TestCase):
    def test_row_height_content(self):
        self.assertIs(style("row-height: content;")["row-height"], CONTENT)

    def test_col_width_content(self):
        self.assertIs(style("col-width: content;")["col-width"], CONTENT)

    def test_min_and_max_content(self):
        self.assertIs(style("col-width: min-content;")["col-width"], MIN_CONTENT)
        self.assertIs(style("col-width: max-content;")["col-width"], MAX_CONTENT)
        self.assertIs(style("row-height: max-content;")["row-height"], MAX_CONTENT)

    def test_whitespace_and_case_tolerated(self):
        self.assertIs(style("row-height:   CONTENT  ;")["row-height"], CONTENT)
        self.assertIs(style("col-width: Max-Content;")["col-width"], MAX_CONTENT)

    def test_modes_and_flags(self):
        self.assertEqual(CONTENT.mode, "content")
        self.assertTrue(MIN_CONTENT.is_min)
        self.assertTrue(MAX_CONTENT.is_max)
        self.assertFalse(CONTENT.is_min)
        self.assertFalse(CONTENT.is_max)

    def test_is_not_a_layout_area_node(self):
        # It must not look like an expression, or compute() would try to
        # evaluate it and blow up on .token_type.
        v = style("row-height: content;")["row-height"]
        self.assertIsInstance(v, ContentSize)
        self.assertFalse(hasattr(v, "token_type"))

    def test_equality_and_hash(self):
        self.assertEqual(ContentSize("content"), CONTENT)
        self.assertNotEqual(ContentSize("min-content"), CONTENT)
        self.assertEqual(len({ContentSize("content"), CONTENT}), 1)


class TestExistingExpressionsUnchanged(unittest.TestCase):
    """Back-compat: every value that parsed before must still parse the same."""

    def _compute(self, text, key="col-width", axis=1024.0, font=20):
        node = style(f"{key}: {text};")[key]
        return LayoutAreaParser.compute(node, None, axis, font)

    def test_bare_digits_are_percent(self):
        self.assertEqual(self._compute("50"), 50.0)

    def test_pixels(self):
        self.assertAlmostEqual(self._compute("512px"), 50.0)

    def test_ems(self):
        # 2em at font 20 == 40px of 1024 == 3.90625%
        self.assertAlmostEqual(self._compute("2em", font=20), (2 * 20 / 1024) * 100)

    def test_min_max_functions_still_work(self):
        self.assertEqual(self._compute("min(10,20)"), 10.0)
        self.assertEqual(self._compute("max(10,20)"), 20.0)

    def test_arithmetic(self):
        self.assertEqual(self._compute("10*3"), 30.0)

    def test_identifier_still_falls_back_to_one(self):
        self.assertEqual(self._compute("somevar"), 1.0)

    def test_area_still_parses_to_four(self):
        self.assertEqual(len(style("area: 0,0,100,50;")["area"]), 4)


class TestKeywordElsewhereIsHarmless(unittest.TestCase):
    """A content keyword outside row-height/col-width must not become a new
    failure mode. It evaluates to 1 -- exactly the pre-existing fallback for an
    unknown identifier."""

    def test_content_inside_area(self):
        nodes = style("area: 0,0,content,50;")["area"]
        self.assertEqual(LayoutAreaParser.compute(nodes[2], None, 1024.0, 20), 1)

    def test_min_content_inside_area_does_not_raise(self):
        # Previously raised: `min` matched, then parse_func hit `-`.
        nodes = style("area: 0,0,min-content,50;")["area"]
        self.assertEqual(LayoutAreaParser.compute(nodes[2], None, 1024.0, 20), 1)

    def test_lexes_as_one_token(self):
        self.assertEqual([t.token_type for t in LayoutAreaParser.lex("min-content")],
                         ["content", "eof"])
        self.assertEqual([t.token_type for t in LayoutAreaParser.lex("max-content")],
                         ["content", "eof"])

    def test_word_starting_with_content_is_still_an_id(self):
        # The \b guard: "contentious" must not lex as the keyword.
        self.assertEqual([t.token_type for t in LayoutAreaParser.lex("contentious")],
                         ["id", "eof"])

    def test_min_prefixed_identifier_unaffected(self):
        self.assertEqual([t.token_type for t in LayoutAreaParser.lex("minimum")],
                         ["min", "id", "eof"])


class TestContentFallsBackToFlexForNow(unittest.TestCase):
    """S1 is plumbing only -- nothing measures yet.

    Until the measure pass lands, a content size must behave as if it were
    absent (flex), never reach arithmetic, and never crash. The important part
    is that it no longer silently resolves to 1%.
    """

    def setUp(self):
        import types
        from sbs_utils.helpers import FrameContext
        from sbs_utils.vec import Vec3
        import sbs_utils.procedural.gui  # noqa: F401  (circular-import order)

        FrameContext.aspect_ratios[0] = Vec3(1024, 768, 0)
        FrameContext.context = types.SimpleNamespace(
            sbs=None, sim=None, event=types.SimpleNamespace(client_id=0))

    def tearDown(self):
        from sbs_utils.helpers import FrameContext
        FrameContext.context = None

    def _layout(self, row_heights):
        from sbs_utils.pages.layout.layout import Layout
        from sbs_utils.pages.layout.row import Row
        from sbs_utils.pages.layout.column import Column

        rows = []
        for h in row_heights:
            r = Row()
            if h is not None:
                # Same value style.py would store, without needing a live task.
                r.set_row_height(style(f"row-height: {h};")["row-height"])
            r.add(Column())
            rows.append(r)
        sec = Layout("t", rows, 0, 0, 100, 100)
        sec.calc(0)
        return rows

    def test_content_row_splits_like_flex(self):
        # Two rows, one content one plain: content is not resolvable yet, so
        # both stay in the flex pool and split 50/50.
        rows = self._layout(["content", None])
        self.assertAlmostEqual(rows[0].height, 50.0)
        self.assertAlmostEqual(rows[1].height, 50.0)

    def test_content_row_is_not_one_percent(self):
        # The old behaviour: 'content' lexed as an id -> 1.0 -> a 1%-tall row.
        rows = self._layout(["content", None])
        self.assertNotAlmostEqual(rows[0].height, 1.0)

    def test_fixed_row_still_wins_alongside_content(self):
        rows = self._layout(["20", "content"])
        self.assertAlmostEqual(rows[0].height, 20.0)
        self.assertAlmostEqual(rows[1].height, 80.0)

    def test_all_three_keywords_are_accepted_on_a_row(self):
        rows = self._layout(["content", "min-content", "max-content"])
        for r in rows:
            self.assertAlmostEqual(r.height, 100.0 / 3.0)

    def test_content_col_width_does_not_crash(self):
        from sbs_utils.pages.layout.layout import Layout
        from sbs_utils.pages.layout.row import Row
        from sbs_utils.pages.layout.column import Column

        r = Row()
        for w in ("content", None):
            c = Column()
            if w is not None:
                c.set_col_width(style(f"col-width: {w};")["col-width"])
            r.add(c)
        sec = Layout("t", [r], 0, 0, 100, 100)
        sec.calc(0)                       # must not raise
        widths = [c.bounds.width for c in r.columns]
        self.assertAlmostEqual(sum(widths), 100.0, places=3)
        # both flex for now, so equal halves
        self.assertAlmostEqual(widths[0], 50.0)


if __name__ == "__main__":
    unittest.main()


class TestCssSpellings(unittest.TestCase):
    """`1fr` is canonical; `auto` is the alias that keeps working.

    The mode formerly called `auto` is an equal share of the leftover space with
    a minimum -- which CSS spells `1fr`. CSS's own `auto` means the opposite
    (size to content, shrink under pressure), so the old name mispredicted the
    behaviour for anyone arriving from CSS, and it is the DEFAULT mode.

    Both spellings resolve to the SAME sentinel today. That is the point: if
    `auto` is ever given its CSS meaning, only scripts that wrote `auto`
    explicitly change behaviour.
    """

    def test_1fr_and_auto_are_the_same_mode(self):
        self.assertIs(StyleDefinition.parse_width("1fr"),
                      StyleDefinition.parse_width("auto"))
        self.assertIs(StyleDefinition.parse_height("1fr"),
                      StyleDefinition.parse_height("auto"))

    def test_1fr_is_the_canonical_name(self):
        self.assertEqual(StyleDefinition.parse_width("auto").mode, "1fr")

    def test_fit_content_is_an_alias_of_content(self):
        self.assertIs(StyleDefinition.parse_width("fit-content"),
                      StyleDefinition.parse_width("content"))

    def test_css_names_survive_whitespace_and_case(self):
        for spelling in (" 1FR ", "Auto", " Fit-Content"):
            with self.subTest(spelling=spelling):
                self.assertIsInstance(StyleDefinition.parse_width(spelling),
                                      ContentSize)

    def test_the_new_spellings_are_harmless_in_an_expression(self):
        # Unsupported positions fall back to 1, exactly like an unknown id --
        # a no-op rather than a new failure mode.
        tokens = LayoutAreaParser.lex("1fr")
        self.assertEqual(tokens[0].token_type, "content")


class TestOverflowSpellings(unittest.TestCase):
    def test_visible_is_an_alias_of_spill(self):
        from sbs_utils.pages.layout.measure import OVERFLOW_ALIASES
        self.assertEqual(OVERFLOW_ALIASES["visible"], "spill")

    def test_hidden_is_deliberately_NOT_an_alias_of_hide(self):
        # CSS `hidden` means draw-and-clip; ours means do-not-draw. Borrowing
        # the word would be more misleading, not less -- this engine cannot clip.
        from sbs_utils.pages.layout.measure import OVERFLOW_ALIASES, OVERFLOW_POLICIES
        self.assertNotIn("hidden", OVERFLOW_ALIASES)
        self.assertNotIn("hidden", OVERFLOW_POLICIES)
