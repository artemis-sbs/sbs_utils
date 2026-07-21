"""`col-width: auto` -- minimum-aware flex, the LM issue 672 behaviour.

The other three keywords take a column OUT of the flex pool and give it a size
of its own. `auto` leaves it IN the pool but puts a floor under it, so a column
whose content needs more than the even share grows and its roomier neighbours
give way.

Because col-width cascades col -> row -> section, `auto` on a section makes
every column in it minimum-aware without annotating any of them. That is the
property issue 672 actually asks for: dynamic layouts that nobody can annotate
in advance.

Metrics are stubbed so these pin the distribution, not the mock's font tables.
"""
import types
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

from sbs_utils.helpers import FrameContext
from sbs_utils.vec import Vec3
from sbs_utils.mast.parsers import StyleDefinition, AUTO

import sbs_utils.procedural.gui  # noqa: F401  (import order: circular via blank)
from sbs_utils.pages.layout.layout import Layout
from sbs_utils.pages.layout.row import Row
from sbs_utils.pages.layout.column import Column
from sbs_utils.pages.layout.text import Text
from sbs_utils.pages.layout import measure


class StubSbs:
    """10px/char, 20px/line."""

    def get_text_line_width(self, font, text):
        return len(text) * 10

    def get_text_line_height(self, font, text):
        return 20

    def get_text_block_height(self, font, text, px_width):
        per_line = max(1, px_width // 10)
        lines, cur = 1, 0
        for word in text.split():
            need = len(word) if cur == 0 else cur + 1 + len(word)
            if need > per_line and cur:
                lines += 1
                cur = len(word)
            else:
                cur = need
        return lines * 20


def _text(label, style=None):
    t = Text("t", f"$text:`{label}`;font:gui-2;")
    if style:
        parsed = StyleDefinition.parse(style)
        if "col-width" in parsed:
            t.set_col_width(parsed["col-width"])
        t.margin_style = parsed.get("margin")
        t.border_style = parsed.get("border")
        t.padding_style = parsed.get("padding")
    return t


class _Base(unittest.TestCase):
    def setUp(self):
        FrameContext.aspect_ratios[0] = Vec3(1000, 1000, 0)
        FrameContext.context = types.SimpleNamespace(
            sbs=StubSbs(), sim=None, event=types.SimpleNamespace(client_id=0))
        measure.measure_cache_clear()

    def tearDown(self):
        FrameContext.context = None
        measure.measure_cache_clear()

    def widths(self, cols, section_style=None):
        row = Row()
        for c in cols:
            row.add(c)
        sec = Layout("sec", [row], 0, 0, 100, 100)
        if section_style:
            sec.set_col_width(StyleDefinition.parse(section_style)["col-width"])
        sec.calc(0)
        return [c.bounds.width for c in row.columns]


class TestAutoRedistributes(_Base):
    def test_long_column_grows_and_neighbours_shrink(self):
        # The issue672b case. "ABCDEFGHIJKLMNOPQRST" is one unbreakable
        # 20-char token == 20% wide; the even share is only 25%... so make it
        # genuinely too big: 40 chars == 40% against a 25% share.
        w = self.widths([_text("A" * 40), _text("a"), _text("b"), _text("c")],
                        "col-width: auto;")
        self.assertAlmostEqual(w[0], 40.0, places=2)
        self.assertAlmostEqual(sum(w), 100.0, places=2)
        for x in w[1:]:
            self.assertLess(x, 25.0, "neighbour did not give up its slack")
            self.assertAlmostEqual(x, 20.0, places=2)

    def test_without_auto_nothing_moves(self):
        # Pins the historical FILL behaviour, so it keeps testing what it means
        # regardless of what layout.AUTO_DEFAULT is set to.
        from sbs_utils.pages.layout import layout as layout_mod
        was = layout_mod.AUTO_DEFAULT
        layout_mod.AUTO_DEFAULT = False
        try:
            w = self.widths([_text("A" * 40), _text("a"), _text("b"), _text("c")])
        finally:
            layout_mod.AUTO_DEFAULT = was
        for x in w:
            self.assertAlmostEqual(x, 25.0, places=2)

    def test_auto_is_a_floor_not_a_size(self):
        # Content that FITS the even share must not shrink to hug its text --
        # that is what `content` is for. `auto` only raises, never lowers.
        w = self.widths([_text("ab"), _text("cd")], "col-width: auto;")
        self.assertAlmostEqual(w[0], 50.0, places=2)
        self.assertAlmostEqual(w[1], 50.0, places=2)

    def test_floor_is_the_widest_word_not_the_whole_string(self):
        # 5 words of 4 chars: min-content is 4 chars == 4%, well under the
        # even share, so nothing moves.
        w = self.widths([_text("aaaa bbbb cccc dddd eeee"), _text("x")],
                        "col-width: auto;")
        self.assertAlmostEqual(w[0], 50.0, places=2)

    def test_two_competing_auto_columns(self):
        w = self.widths([_text("A" * 40), _text("B" * 40)], "col-width: auto;")
        self.assertAlmostEqual(sum(w), 100.0, places=2)
        self.assertAlmostEqual(w[0], w[1], places=2)

    def test_not_enough_room_shares_proportionally(self):
        # Three columns each wanting 40% of a 100% row. They cannot all fit;
        # the row must not overflow and must not go negative.
        w = self.widths([_text("A" * 40), _text("B" * 40), _text("C" * 40)],
                        "col-width: auto;")
        self.assertLessEqual(sum(w), 100.0 + 1e-6)
        for x in w:
            self.assertGreater(x, 0.0)


class TestAutoWithBoxModel(_Base):
    """The floor must include the column's OWN box model.

    This is the bug the issue's real mission exposed: a widget with
    `margin: 3,3,3,3` asked for exactly its text width, then drew that text
    into what was left after 6% of margin.
    """

    # bounds.width is the CONTENT box -- the parent has already subtracted the
    # box model. So the check is that the content box still fits the text: the
    # margined column must end up as wide as the un-margined one, having been
    # allocated extra to cover its margin. Without the fix it lands 10 short
    # and the text is squeezed by exactly the margin.

    def test_margin_does_not_eat_the_text(self):
        # 40-char unbreakable token == 40%, above the 33.3% even share, so the
        # floor is what decides the width.
        plain = self.widths([_text("A" * 40), _text("x"), _text("y")],
                            "col-width: auto;")
        margined = self.widths(
            [_text("A" * 40, "margin: 5,0,5,0;"), _text("x"), _text("y")],
            "col-width: auto;")
        self.assertAlmostEqual(plain[0], 40.0, places=2)
        self.assertAlmostEqual(margined[0], 40.0, places=2,
                               msg="margin was taken out of the text's width")

    def test_padding_and_border_do_not_eat_the_text(self):
        # Three columns, so the 33.3% even share is below the 40% floor and the
        # floor is actually what decides the width.
        plain = self.widths([_text("A" * 40), _text("x"), _text("y")],
                            "col-width: auto;")
        boxed = self.widths(
            [_text("A" * 40, "padding: 2,0,2,0; border: 1,0,1,0;"),
             _text("x"), _text("y")], "col-width: auto;")
        self.assertAlmostEqual(boxed[0], plain[0], places=2)

    def test_content_width_also_accounts_for_the_box(self):
        # Same rule for `content`, not just `auto`.
        plain = self.widths([_text("abcde", "col-width: content;"), _text("x")])
        boxed = self.widths(
            [_text("abcde", "col-width: content; margin: 4,0,4,0;"), _text("x")])
        self.assertAlmostEqual(plain[0], 5.0, places=2)
        self.assertAlmostEqual(boxed[0], 5.0, places=2,
                               msg="margin was taken out of the text's width")


class TestAutoInteractions(_Base):
    def test_fixed_columns_are_untouched(self):
        w = self.widths([_text("A" * 40), _text("fixed", "col-width: 30;"),
                         _text("x")], "col-width: auto;")
        self.assertAlmostEqual(w[1], 30.0, places=2)
        self.assertAlmostEqual(sum(w), 100.0, places=2)

    def test_unmeasurable_column_keeps_a_share(self):
        w = self.widths([_text("A" * 40), Column(), Column()],
                        "col-width: auto;")
        for x in w[1:]:
            self.assertGreater(x, 0.0)

    def test_explicit_content_still_beats_auto_on_a_column(self):
        # A column naming `content` directly is sized to content, even when the
        # section says auto -- the column's own value wins the cascade.
        w = self.widths([_text("abcde", "col-width: content;"), _text("x")],
                        "col-width: auto;")
        self.assertAlmostEqual(w[0], 5.0, places=2)

    def test_auto_parses_and_flags(self):
        self.assertIs(StyleDefinition.parse("col-width: auto;")["col-width"], AUTO)
        self.assertTrue(AUTO.is_auto)
        self.assertFalse(AUTO.is_min)


if __name__ == "__main__":
    unittest.main()
