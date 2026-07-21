"""measure() for the composite / non-text widgets.

Covers the widgets whose natural size is not simply "how wide is my label":
a nested Layout (recursion), an Image (real pixel size), and the two that
deliberately decline to be measured.

The declining ones have tests on purpose. "Returns None" looks like an
oversight to a future maintainer, so the reason is pinned here as well as in
the docstrings.
"""
import types
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

from sbs_utils.helpers import FrameContext
from sbs_utils.vec import Vec3
from sbs_utils.mast.parsers import StyleDefinition, CONTENT

import sbs_utils.procedural.gui  # noqa: F401  (import order: circular via blank)
from sbs_utils.pages.layout.layout import Layout
from sbs_utils.pages.layout.row import Row
from sbs_utils.pages.layout.text import Text
from sbs_utils.pages.layout.dropdown import Dropdown
from sbs_utils.pages.layout.slider import Slider
from sbs_utils.pages.layout import measure


class StubSbs:
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


def _text(label):
    return Text("t", f"$text:`{label}`;font:gui-2;")


def _row(cols):
    r = Row()
    for c in cols:
        r.add(c)
    return r


class _Base(unittest.TestCase):
    def setUp(self):
        self.ar = Vec3(1000, 1000, 0)
        FrameContext.aspect_ratios[0] = self.ar
        FrameContext.context = types.SimpleNamespace(
            sbs=StubSbs(), sim=None, event=types.SimpleNamespace(client_id=0))
        measure.measure_cache_clear()

    def tearDown(self):
        FrameContext.context = None
        measure.measure_cache_clear()


class TestNestedLayoutMeasure(_Base):
    """A sub-section is a Layout stored AS a column, so it must answer the same
    question its own columns do."""

    def test_width_is_the_widest_row(self):
        inner = Layout("inner", [_row([_text("ABCDE")]),          # 5% wide
                                 _row([_text("ABCDEFGHIJ")])],    # 10% wide
                       0, 0, 100, 100)
        w, h = inner.measure(0, CONTENT, None, "gui-2", self.ar)
        self.assertAlmostEqual(w, 10.0, places=3)

    def test_width_sums_columns_within_a_row(self):
        inner = Layout("inner", [_row([_text("ABCDE"), _text("ABCDE")])],
                       0, 0, 100, 100)
        w, _h = inner.measure(0, CONTENT, None, "gui-2", self.ar)
        self.assertAlmostEqual(w, 10.0, places=3)

    def test_height_sums_rows(self):
        inner = Layout("inner", [_row([_text("A")]), _row([_text("B")])],
                       0, 0, 100, 100)
        _w, h = inner.measure(0, CONTENT, None, "gui-2", self.ar)
        self.assertAlmostEqual(h, 4.0, places=3)      # two 20px lines == 4%

    def test_empty_layout_is_unmeasurable(self):
        self.assertIsNone(Layout("e", [], 0, 0, 100, 100)
                          .measure(0, CONTENT, None, "gui-2", self.ar))

    def test_layout_of_unmeasurables_is_unmeasurable(self):
        from sbs_utils.pages.layout.column import Column
        inner = Layout("inner", [_row([Column(), Column()])], 0, 0, 100, 100)
        self.assertIsNone(inner.measure(0, CONTENT, None, "gui-2", self.ar))

    def test_nested_section_sizes_to_content_in_a_parent(self):
        inner = Layout("inner", [_row([_text("ABCDE")])], 0, 0, 100, 100)
        inner.set_col_width(StyleDefinition.parse("col-width: content;")["col-width"])
        outer = Layout("outer", [_row([inner, _text("flex")])], 0, 0, 100, 100)
        outer.calc(0)
        self.assertAlmostEqual(inner.bounds.width, 5.0, places=3)


class TestDeliberatelyUnmeasurable(_Base):
    """These return None ON PURPOSE. Do not "fix" them without reading why."""

    def test_dropdown_declines(self):
        # Its width is the widest option PLUS engine-drawn chrome we cannot
        # ask about. Guessing narrow would draw over the neighbour, since the
        # engine does not clip.
        d = Dropdown("d", "text: a; list: a, bb, ccc;")
        self.assertIsNone(d.measure(0, CONTENT, None, "gui-2", self.ar))

    def test_slider_declines(self):
        s = Slider("s", 0, "low: 0; high: 10;")
        self.assertIsNone(s.measure(0, CONTENT, None, "gui-2", self.ar))

    def test_declining_means_flex_not_zero(self):
        d = Dropdown("d", "text: a; list: a, bb;")
        d.set_col_width(StyleDefinition.parse("col-width: content;")["col-width"])
        outer = Layout("o", [_row([d, _text("flex")])], 0, 0, 100, 100)
        outer.calc(0)
        self.assertGreater(d.bounds.width, 0.0,
                           "an unmeasurable widget collapsed instead of flexing")


class TestImageMeasure(_Base):
    def test_unreadable_image_is_unmeasurable(self):
        from sbs_utils.pages.layout.image import Image
        img = Image("i", "no_such_image_file_xyz")
        # Must be None (-> flex), never (0,0), or a missing asset would silently
        # collapse its column to nothing.
        self.assertIsNone(img.measure(0, CONTENT, None, "gui-2", self.ar))


if __name__ == "__main__":
    unittest.main()
