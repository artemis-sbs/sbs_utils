"""col-width: content -- the width distribution.

Text metrics are stubbed so these test the ALGORITHM, not the mock's font
tables. A recalibration against a new engine capture must not move these
numbers; if it does, the test was measuring the wrong thing.

Stub: 10px per character, 20px per line, screen 1000x1000 so 1% == 10px and a
10-character label is exactly 10% wide. That makes every expectation readable
by inspection rather than a magic constant.
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
from sbs_utils.pages.layout.blank import Blank
from sbs_utils.pages.layout.hole import Hole
from sbs_utils.pages.layout import measure


#
# A content column carries CONTENT_WIDTH_SLACK_PX of deliberate slack: an
# exactly-measured column has no room for rounding at the engine boundary, and
# one pixel short means a wrapped line drawn over the row below (LM issue672).
# SLACK is that constant in percent at this file's 1000px test width, so these
# expectations follow the constant instead of pinning a number.
#
from sbs_utils.pages.layout.layout import CONTENT_WIDTH_SLACK_PX
SLACK = CONTENT_WIDTH_SLACK_PX / 1000.0 * 100.0     # 0.2% at 1000px wide

class StubSbs:
    """10px/char, 20px/line, breaks on whole words."""

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


class _Base(unittest.TestCase):
    def setUp(self):
        FrameContext.aspect_ratios[0] = Vec3(1000, 1000, 0)
        FrameContext.context = types.SimpleNamespace(
            sbs=StubSbs(), sim=None, event=types.SimpleNamespace(client_id=0))
        measure.measure_cache_clear()

    def tearDown(self):
        FrameContext.context = None
        measure.measure_cache_clear()

    def widths(self, cols):
        row = Row()
        for c in cols:
            row.add(c)
        sec = Layout("t", [row], 0, 0, 100, 100)
        sec.calc(0)
        return [c.bounds.width for c in row.columns]


class TestContentWidth(_Base):
    def test_content_column_takes_its_natural_width(self):
        # "HELLO" == 5 chars == 50px == 5% of a 1000px screen.
        w = self.widths([_text("HELLO", "content"), _text("other")])
        self.assertAlmostEqual(w[0], 5.0 + SLACK, places=3)
        self.assertAlmostEqual(w[1], 95.0 - SLACK, places=3)

    def test_longer_text_takes_more(self):
        w = self.widths([_text("HELLO WORLD!", "content"), _text("x")])
        self.assertAlmostEqual(w[0], 12.0 + SLACK, places=3)

    def test_two_content_columns(self):
        w = self.widths([_text("ABCDE", "content"),
                         _text("ABCDEFGHIJ", "content"),
                         _text("flex")])
        self.assertAlmostEqual(w[0], 5.0 + SLACK, places=3)
        self.assertAlmostEqual(w[1], 10.0 + SLACK, places=3)
        self.assertAlmostEqual(w[2], 85.0 - 2 * SLACK, places=3)

    def test_content_plus_fixed_plus_flex(self):
        w = self.widths([_text("ABCDE", "content"), _text("f", 25), _text("flex")])
        self.assertAlmostEqual(w[0], 5.0 + SLACK, places=3)
        self.assertAlmostEqual(w[1], 25.0, places=3)
        self.assertAlmostEqual(w[2], 70.0 - SLACK, places=3)

    def test_all_content_leaves_the_rest_unclaimed(self):
        # No flex column, so the row simply does not fill. Content is a
        # request for a natural size, not a demand for the whole row.
        w = self.widths([_text("ABCDE", "content"), _text("ABCDE", "content")])
        self.assertAlmostEqual(w[0], 5.0 + SLACK, places=3)
        self.assertAlmostEqual(w[1], 5.0 + SLACK, places=3)

    def test_max_content_ignores_available_width(self):
        w = self.widths([_text("ABCDEFGHIJ", "max-content"), _text("flex")])
        self.assertAlmostEqual(w[0], 10.0 + SLACK, places=3)

    def test_min_content_is_the_widest_word(self):
        # "AB CDEFG H" -> widest token is CDEFG == 5 chars == 5%.
        w = self.widths([_text("AB CDEFG H", "min-content"), _text("flex")])
        self.assertAlmostEqual(w[0], 5.0 + SLACK, places=3)

    def test_empty_text_collapses(self):
        w = self.widths([_text("", "content"), _text("flex")])
        self.assertAlmostEqual(w[0], 0.0, places=3)
        self.assertAlmostEqual(w[1], 100.0, places=3)


class TestOverflowShrinkOrder(_Base):
    """Flex starves first; content shrinks only to min-content."""

    def test_flex_is_starved_before_content_shrinks(self):
        # Content wants 60%, fixed takes 40% -> flex must go to 0, and the
        # content column must NOT be squeezed.
        c = _text("A" * 60, "content")
        w = self.widths([c, _text("f", 40), _text("flex")])
        self.assertAlmostEqual(w[0], 60.0, places=3)
        self.assertAlmostEqual(w[1], 40.0, places=3)
        self.assertAlmostEqual(w[2], 0.0, places=3)

    def test_content_shrinks_when_it_cannot_fit(self):
        # Two content columns wanting 80% each = 160% of the row. They shrink
        # proportionally toward min-content rather than overflowing outright.
        w = self.widths([_text("A " * 40, "content"), _text("B " * 40, "content")])
        self.assertLessEqual(sum(w), 100.0 + 1e-6, f"row overflows: {w}")

    def test_content_never_shrinks_below_min_content(self):
        # A single unbreakable 60-char word cannot go below 60% no matter what
        # else is in the row -- past that the engine breaks mid-word and, since
        # it does not clip, the glyphs spill sideways.
        w = self.widths([_text("A" * 60, "content"), _text("f", 80)])
        self.assertAlmostEqual(w[0], 60.0, places=3)


class TestUnmeasurableFallsBackToFlex(_Base):
    """The property that makes a section-level `col-width: content` safe."""

    def test_plain_column_is_unmeasurable_and_stays_flex(self):
        # A bare Column has no content, so measure() returns None. It must take
        # a flex share, NOT collapse to zero.
        w = self.widths([Column(), _text("ABCDE", "content")])
        self.assertGreater(w[0], 0.0)

    def test_section_level_content_does_not_zero_unmeasurable_columns(self):
        row = Row()
        row.add(Column())                 # unmeasurable
        row.add(_text("ABCDE"))           # measurable, inherits from section
        sec = Layout("t", [row], 0, 0, 100, 100)
        sec.set_col_width(StyleDefinition.parse("col-width: content;")["col-width"])
        sec.calc(0)
        widths = [c.bounds.width for c in row.columns]
        self.assertGreater(widths[0], 0.0, "unmeasurable column collapsed")

    def test_square_ignores_content_width(self):
        c = _text("ABCDEFGHIJKLMNOP", "content")
        c.square = True
        w = self.widths([c, _text("flex")])
        # Sized as a square from the row height, not from its 16-char text.
        self.assertNotAlmostEqual(w[0], 16.0, places=3)

    def test_blank_is_flex_unless_it_opts_in(self):
        # Without the keyword a Blank is an ordinary flex spacer and takes its
        # share -- measure() is only consulted for content-sized columns.
        w = self.widths([Blank(), _text("ABCDE", "content"), _text("flex")])
        self.assertGreater(w[0], 0.0)

    def test_blank_collapses_when_content_sized(self):
        b = Blank()
        b.set_col_width(StyleDefinition.parse("col-width: content;")["col-width"])
        w = self.widths([b, _text("flex")])
        self.assertAlmostEqual(w[0], 0.0, places=3)
        self.assertAlmostEqual(w[1], 100.0, places=3)

    def test_hole_still_donates(self):
        row = Row()
        row.add(Hole())
        row.add(_text("ABCDE", "content"))
        sec = Layout("t", [row], 0, 0, 100, 100)
        sec.calc(0)
        # Hole donates its share to the next column, which is content-sized.
        self.assertGreater(row.columns[1].bounds.width, 5.0)


class TestContentSizedFlag(_Base):
    """Only columns actually measured get flagged, since the flag is what
    later decides whether a value change forces a re-layout."""

    def test_flag_set_on_measured_column(self):
        c = _text("ABCDE", "content")
        self.widths([c, _text("flex")])
        self.assertTrue(c.content_sized)

    def test_flag_not_set_without_the_keyword(self):
        # With AUTO_DEFAULT on, an unsized text column IS measured (for its
        # min-content floor), so this pins the pure-FILL default explicitly.
        from sbs_utils.pages.layout import layout as layout_mod
        was = layout_mod.AUTO_DEFAULT
        layout_mod.AUTO_DEFAULT = False
        try:
            c = _text("ABCDE")
            self.widths([c, _text("flex")])
        finally:
            layout_mod.AUTO_DEFAULT = was
        self.assertFalse(c.content_sized)

    def test_flag_not_set_on_unmeasurable(self):
        c = Column()
        c.set_col_width(StyleDefinition.parse("col-width: content;")["col-width"])
        self.widths([c, _text("flex")])
        self.assertFalse(c.content_sized)


class TestMeasurementIsCached(_Base):
    def test_repeated_calc_does_not_remeasure_from_the_engine(self):
        c = _text("ABCDE", "content")
        row = Row()
        row.add(c)
        row.add(_text("flex"))
        sec = Layout("t", [row], 0, 0, 100, 100)
        sec.calc(0)
        after_first = measure.measure_cache_stats()["engine_calls"]
        for _ in range(5):
            sec.calc(0)
        self.assertEqual(measure.measure_cache_stats()["engine_calls"], after_first)


if __name__ == "__main__":
    unittest.main()
