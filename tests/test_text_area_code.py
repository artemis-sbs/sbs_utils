"""gui_text_area rendering SOURCE: markdown=False plus caller-supplied line styles.

A text area mangles code, because every markup character it interprets is a
character code uses: `#` is a MAST comment, `-` starts `->END`, and any `[...]`
is read as a link reference and REPLACES the line with its remainder. So a code
view used to be built out of a listbox of one gui_text per line, which
reimplemented -- badly -- the wrapping and scrolling a text area already has.

markdown=False turns the interpretation off. line_styles is how the result still
gets colour and indentation: a style already carries both, and the caller is the
thing that knows a line is a comment and knows its depth.
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest

from cosmos_dev.mock import sbs
from sbs_utils.helpers import FrameContext, Context, FakeEvent
from sbs_utils.pages.layout.text_area import TextArea, TextLine
from sbs_utils.pages.layout.layout import Bounds

NL = chr(10)


class TestTextAreaCode(unittest.TestCase):
    def setUp(self):
        sbs.create_new_sim()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent())

    def _calc(self, text, area=(0, 0, 80, 60), **kw):
        # A single line with no marker takes the simple_text fast path in the
        # value setter and never builds TextLines, so every case here is
        # multi-line -- which is what a code view is anyway.
        ta = TextArea("t", text, **kw)
        ta.bounds = Bounds(*area)
        ta.calc_rich(0)
        return ta

    def _texts(self, ta):
        return [ln.text for ln in ta.lines if isinstance(ln, TextLine)]

    # -- markdown OFF keeps the characters -----------------------------------

    def test_hash_is_not_a_heading(self):
        """A MAST comment must survive as a comment, marker included."""
        src = "# spawn the escort" + NL + "npc_spawn(0, 0, 0)"
        out = self._texts(self._calc(src, markdown=False))
        self.assertTrue(any(t.startswith("# spawn the escort") for t in out), out)

    def test_dash_is_not_a_bullet(self):
        src = "->END if obj is None" + NL + "next_line()"
        out = self._texts(self._calc(src, markdown=False))
        self.assertTrue(any("->END" in t for t in out), out)

    def test_brackets_survive(self):
        """The sharpest one: rule_link_ref replaces the line with its remainder,
        so a subscript used to eat everything before it."""
        src = "name = item['key']" + NL + "next_line()"
        out = self._texts(self._calc(src, markdown=False))
        self.assertTrue(any("item['key']" in t for t in out), out)

    def test_leading_digit_is_not_a_list(self):
        src = "3 * scale" + NL + "next_line()"
        out = self._texts(self._calc(src, markdown=False))
        self.assertTrue(any(t.startswith("3 * scale") for t in out), out)

    def test_markdown_still_parses_by_default(self):
        """Default behaviour is untouched -- the marker is consumed as markup."""
        out = self._texts(self._calc("# A heading" + NL + "body text"))
        self.assertFalse(any(t.startswith("#") for t in out), out)

    # -- caller-supplied styles ----------------------------------------------

    def test_line_style_applied_per_line(self):
        styles = [{"style": "font:gui-1;color:#6a8;", "indent": 0},
                  {"style": "font:gui-1;color:#cde;", "indent": 4}]
        ta = self._calc("# a comment" + NL + "code_here()",
                        markdown=False, line_styles=styles)
        lines = [ln for ln in ta.lines if isinstance(ln, TextLine)]
        self.assertEqual(lines[0].style.get("indent"), 0)
        self.assertEqual(lines[1].style.get("indent"), 4)
        self.assertIn("#6a8", lines[0].style.get("style"))
        self.assertIn("#cde", lines[1].style.get("style"))

    def test_partial_line_style_is_normalised(self):
        """A caller should be able to pass only what it cares about."""
        ta = TextArea("t", "x", markdown=False, line_styles=[{"indent": 2}])
        st = ta.line_style_for(0)
        self.assertEqual(st["indent"], 2)
        self.assertIn("style", st)
        self.assertEqual(st["prepend"], "")

    def test_missing_line_style_falls_back(self):
        ta = TextArea("t", "a" + NL + "b", markdown=False,
                      line_styles=[{"indent": 3}])
        self.assertEqual(ta.line_style_for(0)["indent"], 3)
        self.assertIsNone(ta.line_style_for(1))     # shorter list is fine
        self.assertIsNone(ta.line_style_for(9))

    # -- C: the indent comes off the wrap width -------------------------------

    def test_indent_reduces_the_wrap_width(self):
        """The send rect is shifted right by the indent, so wrapping has to
        happen against what is LEFT. Measuring at the full width and drawing
        narrower makes the engine wrap a line we did not count -- and it does not
        clip, so that line lands on top of its neighbour."""
        text = " ".join(["word"] * 40) + NL + "tail"

        def rendered(indent):
            ta = self._calc(text, markdown=False,
                            line_styles=[{"indent": indent}, {"indent": indent}])
            return len(self._texts(ta))

        # Deep enough to cross a wrap boundary at this width -- a small indent
        # narrows the box without necessarily changing the line count, so a
        # near-zero comparison would pass whether or not the fix were present.
        self.assertGreater(rendered(60), rendered(0))
        # And monotonic: narrower box, never fewer lines.
        counts = [rendered(i) for i in (0, 20, 40, 60)]
        self.assertEqual(counts, sorted(counts), counts)


if __name__ == "__main__":
    unittest.main()
