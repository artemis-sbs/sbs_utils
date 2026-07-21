"""`overflow:` -- what to do when text cannot fit its rect.

The engine does not clip, so text that does not fit is DRAWN anyway, over its
neighbours. The layout tries to size things so that never happens, but some
text cannot fit at any width: one unbreakable word wider than its row, or a
paragraph in a band whose height the author fixed.

`overflow:` lets the author choose. Everything it can do is expressible through
send_gui_* -- change the font, change the string, or do not send -- because
asking the engine to clip is not an option that exists.

Default stays `spill`: it is the historical behaviour, and a visible failure
gets fixed while a silent one does not.
"""
import types
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

from sbs_utils.helpers import FrameContext, props_display_text, props_font
from sbs_utils.vec import Vec3
from sbs_utils.mast.parsers import StyleDefinition

import sbs_utils.procedural.gui  # noqa: F401  (import order: circular via blank)
from sbs_utils.pages.layout.bounds import Bounds
from sbs_utils.pages.layout import measure


class StubSbs:
    """Per-font char widths so shrinking has a real ladder to walk."""
    W = {"smallest": 4, "gui-1": 6, "gui-2": 8, "gui-3": 10,
         "gui-4": 14, "gui-5": 18, "gui-6": 26}
    H = {"smallest": 8, "gui-1": 12, "gui-2": 16, "gui-3": 20,
         "gui-4": 28, "gui-5": 36, "gui-6": 52}

    def get_text_line_width(self, font, text):
        return len(text) * self.W.get(font, 10)

    def get_text_line_height(self, font, text):
        return self.H.get(font, 20)

    def get_text_block_height(self, font, text, px_width):
        per_line = max(1, px_width // self.W.get(font, 10))
        lines = max(1, -(-len(text) // per_line))     # ceil
        return lines * self.H.get(font, 20)


class _Base(unittest.TestCase):
    def setUp(self):
        FrameContext.aspect_ratios[0] = Vec3(1000, 1000, 0)
        FrameContext.context = types.SimpleNamespace(
            sbs=StubSbs(), sim=None, event=types.SimpleNamespace(client_id=0))
        measure.measure_cache_clear()

    def tearDown(self):
        FrameContext.context = None
        measure.measure_cache_clear()

    def apply(self, text, policy, w_pct, h_pct=10.0, font="gui-3"):
        props = f"$text:`{text}`;font:{font};"
        b = Bounds(0, 0, w_pct, h_pct)
        return measure.apply_overflow(props, b, policy)


class TestSpillIsTheDefault(_Base):
    def test_none_policy_is_untouched(self):
        props, draw = self.apply("X" * 40, None, 10.0)
        self.assertTrue(draw)
        self.assertIn("X" * 40, props)

    def test_explicit_spill_is_untouched(self):
        props, draw = self.apply("X" * 40, "spill", 10.0)
        self.assertTrue(draw)
        self.assertIn("X" * 40, props)


class TestShrink(_Base):
    def test_steps_down_until_it_fits(self):
        # NOTE shrink fits the BOX, not one line. Text wider than the box is
        # not itself a failure -- it wraps. What fails is wrapping to more
        # HEIGHT than the box has, because the engine draws the extra lines
        # anyway. So the box has to be short for shrinking to be needed.
        #
        # 20 chars in 100x20px: gui-3 wraps to 2 lines (40px) - too tall.
        # gui-2 -> 32px, gui-1 -> 24px, smallest -> one line of 8px, fits.
        props, draw = self.apply("X" * 20, "shrink", 10.0, h_pct=2.0)
        self.assertTrue(draw)
        self.assertEqual(props_font(props), "smallest")

    def test_wide_but_wrapping_text_is_left_alone(self):
        # Wider than the box, but it wraps and the box is tall enough. Nothing
        # is drawn outside, so there is nothing to fix.
        props, _ = self.apply("X" * 20, "shrink", 10.0, h_pct=10.0)
        self.assertEqual(props_font(props), "gui-3")

    def test_picks_the_largest_that_fits(self):
        # 10 chars in a 100px box: gui-3 needs 100 -> already fits, unchanged.
        props, draw = self.apply("X" * 10, "shrink", 10.0)
        self.assertEqual(props_font(props), "gui-3")

    def test_never_grows(self):
        # Plenty of room -- shrink must not promote a small font.
        props, _ = self.apply("Hi", "shrink", 50.0, font="gui-1")
        self.assertEqual(props_font(props), "gui-1")

    def test_gives_up_and_spills_when_even_smallest_fails(self):
        # 200 chars in a 50x2px box wraps to many lines at every font.
        props, draw = self.apply("X" * 200, "shrink", 5.0, h_pct=0.2)
        self.assertTrue(draw, "shrink must fall back to spilling, not hiding")
        self.assertEqual(props_font(props), "gui-3", "font should be left alone")

    def test_text_is_never_altered(self):
        props, _ = self.apply("Hello World", "shrink", 5.0)
        self.assertEqual(props_display_text(props), "Hello World")


class TestEllipsis(_Base):
    def test_truncates_with_ascii_dots(self):
        props, draw = self.apply("ABCDEFGHIJKLMNOP", "ellipsis", 10.0)
        self.assertTrue(draw)
        out = props_display_text(props)
        self.assertTrue(out.endswith("..."), out)
        self.assertLess(len(out), len("ABCDEFGHIJKLMNOP"))

    def test_result_actually_fits(self):
        props, _ = self.apply("ABCDEFGHIJKLMNOP", "ellipsis", 10.0)
        out = props_display_text(props)
        self.assertLessEqual(len(out) * 10, 100)

    def test_text_that_fits_is_untouched(self):
        props, _ = self.apply("ABCDE", "ellipsis", 10.0)
        self.assertEqual(props_display_text(props), "ABCDE")

    def test_spills_rather_than_showing_only_dots(self):
        # A box too small even for "..." -- truncating would show nothing but
        # punctuation, which is worse than spilling.
        props, draw = self.apply("ABCDEFGH", "ellipsis", 2.0)
        self.assertTrue(draw)
        self.assertEqual(props_display_text(props), "ABCDEFGH")


class TestHide(_Base):
    def test_hides_when_it_does_not_fit(self):
        _props, draw = self.apply("X" * 40, "hide", 5.0, h_pct=2.0)
        self.assertFalse(draw)

    def test_draws_when_it_fits(self):
        _props, draw = self.apply("Hi", "hide", 50.0, h_pct=10.0)
        self.assertTrue(draw)


class TestStylePlumbing(_Base):
    def test_overflow_parses_and_applies(self):
        from sbs_utils.pages.layout.text import Text
        from sbs_utils.procedural.style import apply_style_def

        class _T:
            class _M:
                class _P:
                    client_id = 0
                page = _P()
            main = _M()

            def format_string(self, s):
                return s

        t = Text("t", "$text:`Hi`;")
        apply_style_def(StyleDefinition.parse("overflow: shrink;"), t, _T())
        self.assertEqual(t.overflow, "shrink")

    def test_default_is_none(self):
        from sbs_utils.pages.layout.column import Column
        self.assertIsNone(Column().overflow)


class TestUnmeasurableIsLeftAlone(_Base):
    def test_no_context_does_not_hide_anything(self):
        FrameContext.context = None
        props, draw = self.apply("X" * 40, "hide", 1.0)
        self.assertTrue(draw, "must not hide text it could not measure")


if __name__ == "__main__":
    unittest.main()
