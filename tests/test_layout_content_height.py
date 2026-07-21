"""row-height: content -- the height distribution, and the square cycle.

Metrics are stubbed (10px/char, 20px per LINE, 1000x1000 screen) so these pin
the algorithm rather than the mock's font tables. 20px == 2% of the screen, so
a one-line row is 2% tall and a three-line row is 6%.

The wrap in the stub is deliberate: content heights only mean anything if the
height actually responds to the width the column is given, and the ordering bug
that would break that (measuring height before widths are known) is invisible
without a wrapping case.
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
from sbs_utils.pages.layout.text import Text
from sbs_utils.pages.layout import measure


class StubSbs:
    """10px/char, 20px per line, greedy whole-word wrap."""

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


def _text(label, width=None):
    t = Text("t", f"$text:`{label}`;font:gui-2;")
    if width is not None:
        t.set_col_width(StyleDefinition.parse(f"col-width: {width};")["col-width"])
    return t


def _row(cols, height=None):
    r = Row()
    for c in cols:
        r.add(c)
    if height is not None:
        r.set_row_height(StyleDefinition.parse(f"row-height: {height};")["row-height"])
    return r


class _Base(unittest.TestCase):
    def setUp(self):
        FrameContext.aspect_ratios[0] = Vec3(1000, 1000, 0)
        FrameContext.context = types.SimpleNamespace(
            sbs=StubSbs(), sim=None, event=types.SimpleNamespace(client_id=0))
        measure.measure_cache_clear()

    def tearDown(self):
        FrameContext.context = None
        measure.measure_cache_clear()

    def heights(self, rows, bottom=100):
        sec = Layout("t", rows, 0, 0, 100, bottom)
        sec.calc(0)
        return [r.height for r in rows]


class TestContentRowHeight(_Base):
    def test_single_line_row_takes_one_line(self):
        h = self.heights([_row([_text("HELLO")], "content"), _row([_text("x")])])
        self.assertAlmostEqual(h[0], 2.0, places=3)      # 20px == 2%
        self.assertAlmostEqual(h[1], 98.0, places=3)

    def test_rows_sum_to_the_section(self):
        h = self.heights([_row([_text("A")], "content"),
                          _row([_text("B")], "content"),
                          _row([_text("C")])])
        self.assertAlmostEqual(sum(h), 100.0, places=3)

    def test_taller_column_wins(self):
        # Two columns in one row; the row is as tall as the taller content.
        wide = _text(" ".join(["word"] * 30))    # wraps in its half-width column
        h = self.heights([_row([_text("short"), wide], "content"), _row([_text("x")])])
        self.assertGreater(h[0], 2.0)

    def test_max_content_is_one_line_regardless_of_width(self):
        # max-content does not wrap by definition, so a long string is still
        # a single line tall.
        long_text = " ".join(["word"] * 30)
        h = self.heights([_row([_text(long_text)], "max-content"), _row([_text("x")])])
        self.assertAlmostEqual(h[0], 2.0, places=3)

    def test_min_content_aliases_content_on_a_row(self):
        a = self.heights([_row([_text("HELLO")], "content"), _row([_text("x")])])
        b = self.heights([_row([_text("HELLO")], "min-content"), _row([_text("x")])])
        self.assertAlmostEqual(a[0], b[0], places=6)

    def test_fixed_and_content_and_flex_together(self):
        h = self.heights([_row([_text("A")], 30),
                          _row([_text("B")], "content"),
                          _row([_text("C")])])
        self.assertAlmostEqual(h[0], 30.0, places=3)
        self.assertAlmostEqual(h[1], 2.0, places=3)
        self.assertAlmostEqual(h[2], 68.0, places=3)


class TestHeightDependsOnWidth(_Base):
    """The ordering guarantee: widths must resolve BEFORE height is measured.

    If height were measured before column widths were known, these two would
    come out the same. They must not.
    """

    def test_narrow_column_wraps_taller(self):
        text = " ".join(["word"] * 20)          # 99 chars
        wide = self.heights([_row([_text(text, 80), _text("x")], "content"),
                             _row([_text("y")])])
        narrow = self.heights([_row([_text(text, 20), _text("x")], "content"),
                               _row([_text("y")])])
        self.assertGreater(narrow[0], wide[0],
                           "row height did not respond to column width")

    def test_column_box_model_reduces_wrap_width(self):
        text = " ".join(["word"] * 20)
        plain = _text(text, 40)
        padded = _text(text, 40)
        padded.padding_style = StyleDefinition.parse("padding: 5,0,5,0;")["padding"]
        a = self.heights([_row([plain], "content"), _row([_text("y")])])
        b = self.heights([_row([padded], "content"), _row([_text("y")])])
        self.assertGreater(b[0], a[0], "padding did not narrow the wrap width")


class TestSquaresInContentRows(_Base):
    """Squares are sized FROM the row height and CONSUME width, so a content
    row containing one is genuinely circular. See _content_row_height."""

    def test_square_does_not_contribute_to_height(self):
        sq = _text("A" * 40)
        sq.square = True
        # Row height must come from the text column, not the square.
        h = self.heights([_row([sq, _text("HELLO")], "content"), _row([_text("x")])])
        self.assertAlmostEqual(h[0], 2.0, places=3)

    def test_row_of_only_squares_falls_back_to_flex(self):
        a, b = _text("A"), _text("B")
        a.square = b.square = True
        h = self.heights([_row([a, b], "content"), _row([_text("x")])])
        # Nothing measurable -> no natural height -> flex, so 50/50.
        self.assertAlmostEqual(h[0], 50.0, places=3)

    def test_row_of_only_unmeasurable_falls_back_to_flex(self):
        h = self.heights([_row([Column(), Column()], "content"), _row([_text("x")])])
        self.assertAlmostEqual(h[0], 50.0, places=3)

    def test_square_row_resolves_and_stays_bounded(self):
        sq = _text("A")
        sq.square = True
        h = self.heights([_row([sq, _text("HELLO WORLD")], "content"),
                          _row([_text("x")])])
        self.assertGreater(h[0], 0.0)
        self.assertLess(h[0], 100.0)
        self.assertAlmostEqual(sum(h), 100.0, places=3)


class TestOverflowingContentRows(_Base):
    """Content rows are requests. They scale down rather than starving flex."""

    def test_content_rows_scale_when_oversubscribed(self):
        tall = " ".join(["word"] * 400)         # wraps to far more than 100%
        h = self.heights([_row([_text(tall)], "content"),
                          _row([_text(tall)], "content"),
                          _row([_text("x")])])
        self.assertLessEqual(sum(h), 100.0 + 1e-6, f"section overflows: {h}")
        self.assertGreaterEqual(h[2], -1e-6, f"flex row went negative: {h}")

    def test_fixed_rows_are_never_scaled(self):
        # An over-large FIXED row already drove the remainder negative before
        # content sizing existed; that behaviour must be untouched.
        h = self.heights([_row([_text("A")], 70), _row([_text("B")], 70)])
        self.assertAlmostEqual(h[0], 70.0, places=3)
        self.assertAlmostEqual(h[1], 70.0, places=3)


if __name__ == "__main__":
    unittest.main()
