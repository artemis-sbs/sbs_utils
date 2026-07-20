"""Precision/recall for the audit's TEXT_WIDE / TEXT_TALL checks.

The rect checks (OVERFLOW/OVERLAP/DEGENERATE) reason about boxes. They cannot
see a CORRECTLY sized box holding text too big for it -- and the engine draws
that text anyway, unclipped, over its neighbours. These tests cover the check
that closes that gap.

A fake sbs supplies the text metrics, so the geometry is exact and the
assertions do not move when the mock is recalibrated against a new engine
capture.
"""
import unittest

from cosmos_dev.layout_audit import LayoutAudit


class FakeSbs:
    """10px per char wide; 20px per line; wraps on whole words at the box."""

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


def _kinds(a):
    return sorted(k for k, _ in a._findings.values())


def _msgs(a):
    return " | ".join(m for _, m in a._findings.values())


class TextFitBase(unittest.TestCase):
    def setUp(self):
        self.a = LayoutAudit()
        self.a._sbs = FakeSbs()
        self.a._aspect = (1000.0, 1000.0)   # 1% == 10px, so sums are obvious


class TestTextFitRecall(TextFitBase):
    """Real text overflow IS flagged."""

    def test_text_wider_than_its_box(self):
        # box 0..20% of a 1000px screen == 200px; "X"*30 needs 300px.
        self.a.record("send_gui_text", 0, "", "t", 0, 0, 0, 20, 10,
                      "$text:`" + "X" * 30 + "`;font:gui-2;")
        self.a.complete(0, "")
        self.assertIn("TEXT_WIDE", _kinds(self.a))
        self.assertIn("needs 300px", _msgs(self.a))
        self.assertIn("box is 200px", _msgs(self.a))

    def test_wrapped_text_taller_than_its_box(self):
        # 200px wide box fits 20 chars/line; 60 chars of words -> 3 lines ->
        # 60px, but the box is only 0..2% == 20px tall.
        words = " ".join(["word"] * 12)          # 59 chars
        self.a.record("send_gui_text", 0, "", "t", 0, 0, 0, 20, 2,
                      "$text:`" + words + "`;font:gui-2;")
        self.a.complete(0, "")
        self.assertIn("TEXT_TALL", _kinds(self.a))

    def test_button_text_is_checked_too(self):
        self.a.record("send_gui_button", 0, "", "b", 0, 0, 0, 5, 10,
                      "$text:`Launch All Fighters`;font:gui-2;")
        self.a.complete(0, "")
        self.assertIn("TEXT_WIDE", _kinds(self.a))


class TestTextFitPrecision(TextFitBase):
    """Clean layouts stay quiet."""

    def test_text_that_fits_is_not_flagged(self):
        self.a.record("send_gui_text", 0, "", "t", 0, 0, 0, 50, 10,
                      "$text:`Hello`;font:gui-2;")
        self.a.complete(0, "")
        self.assertEqual(_kinds(self.a), [])

    def test_exact_fit_is_not_flagged(self):
        # 20 chars == 200px == exactly the box width.
        self.a.record("send_gui_text", 0, "", "t", 0, 0, 0, 20, 10,
                      "$text:`" + "X" * 20 + "`;font:gui-2;")
        self.a.complete(0, "")
        self.assertNotIn("TEXT_WIDE", _kinds(self.a))

    def test_empty_text_is_not_flagged(self):
        self.a.record("send_gui_text", 0, "", "t", 0, 0, 0, 1, 1, "$text:;font:gui-2;")
        self.a.complete(0, "")
        self.assertEqual(_kinds(self.a), [])

    def test_non_text_widget_is_not_measured(self):
        self.a.record("send_gui_icon", 0, "", "i", 0, 0, 0, 1, 1, None)
        self.a.complete(0, "")
        self.assertEqual(_kinds(self.a), [])

    def test_disabled_without_aspect(self):
        self.a._aspect = None
        self.a.record("send_gui_text", 0, "", "t", 0, 0, 0, 1, 1,
                      "$text:`" + "X" * 99 + "`;font:gui-2;")
        self.a.complete(0, "")
        self.assertEqual(_kinds(self.a), [])

    def test_disabled_without_sbs(self):
        self.a._sbs = None
        self.a.record("send_gui_text", 0, "", "t", 0, 0, 0, 1, 1,
                      "$text:`" + "X" * 99 + "`;font:gui-2;")
        self.a.complete(0, "")
        self.assertEqual(_kinds(self.a), [])


class TestNestedRegionPixels(TextFitBase):
    """Rects are percent-LOCAL at every depth, so the pixel box is the product
    down the sub_region chain. Getting that wrong is the easiest way to make
    the whole check meaningless."""

    def test_text_measured_against_nested_region_size(self):
        # A 50%-wide region of a 1000px screen is 500px; a 20% box inside it is
        # 100px -- NOT 200px. 15 chars == 150px, so it overflows only if the
        # nesting is resolved correctly.
        self.a.record("send_gui_sub_region", 0, "", "reg", 0, 0, 0, 50, 100, None)
        self.a.record("send_gui_text", 0, "reg", "t", 0, 0, 0, 20, 10,
                      "$text:`" + "X" * 15 + "`;font:gui-2;")
        self.a.complete(0, "")
        self.assertIn("TEXT_WIDE", _kinds(self.a))
        self.assertIn("box is 100px", _msgs(self.a))

    def test_unresolvable_region_is_skipped(self):
        # parent region never declared -> we cannot know the pixel size, so we
        # must stay silent rather than guess.
        self.a.record("send_gui_text", 0, "ghost", "t", 0, 0, 0, 20, 10,
                      "$text:`" + "X" * 99 + "`;font:gui-2;")
        self.a.complete(0, "")
        self.assertEqual(_kinds(self.a), [])

    def test_region_cycle_does_not_hang(self):
        self.a.record("send_gui_sub_region", 0, "b", "a", 0, 0, 0, 50, 50, None)
        self.a.record("send_gui_sub_region", 0, "a", "b", 0, 0, 0, 50, 50, None)
        self.a.record("send_gui_text", 0, "a", "t", 0, 0, 0, 20, 10,
                      "$text:`" + "X" * 99 + "`;font:gui-2;")
        self.a.complete(0, "")   # must return, not spin
        self.assertEqual(_kinds(self.a), [])


class TestFontSelection(TextFitBase):
    """The font a widget declares wins at render time, so it must win here."""

    def test_declared_font_is_reported(self):
        self.a.record("send_gui_text", 0, "", "t", 0, 0, 0, 20, 10,
                      "$text:`" + "X" * 30 + "`;font:gui-4;")
        self.a.complete(0, "")
        self.assertIn("font gui-4", _msgs(self.a))

    def test_undeclared_font_falls_back_conservatively(self):
        # No font: measure with the SMALLEST so a finding means "overflows even
        # at the smallest font". Precision over recall -- findings must be real.
        self.a.record("send_gui_text", 0, "", "t", 0, 0, 0, 20, 10,
                      "$text:`" + "X" * 30 + "`;")
        self.a.complete(0, "")
        self.assertIn("font assumed 'smallest'", _msgs(self.a))


class TestPropsParsing(TextFitBase):
    """Local props parsing must match helpers.split_props on the cases that
    matter, especially backtick quoting (issue #569)."""

    def test_colon_inside_backticks_is_literal(self):
        # If ':' inside the backticks split the value, the measured text would
        # be wrong. 24 chars == 240px > 200px box.
        self.a.record("send_gui_text", 0, "", "t", 0, 0, 0, 20, 10,
                      "$text:`Warp: 3; status green`;font:gui-2;")
        self.a.complete(0, "")
        self.assertIn("Warp: 3; status green", _msgs(self.a))


if __name__ == "__main__":
    unittest.main()
