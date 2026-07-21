"""A font tag from a style string must be stored stripped.

Unlike every other style value, a font tag is handed to the engine as a bare
API argument -- get_text_line_width(fontTag, text) -- rather than embedded in a
props string that the engine parses itself. The engine does not recognise
" gui-3" and returns -1, which became a negative column width and an inverted
rect: the widget silently vanished (LM issue672, line 47).

Authors write `font: gui-3` with a space after the colon, which is the natural
spelling, so this has to be normalised rather than documented away.
"""
import types
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

from sbs_utils.helpers import FrameContext
from sbs_utils.vec import Vec3

import sbs_utils.procedural.gui  # noqa: F401  (import order: circular via blank)
from sbs_utils.mast.parsers import StyleDefinition
from sbs_utils.pages.layout.text import Text
from sbs_utils.procedural.style import apply_style_def


class _Task:
    """Minimal stand-in for the MAST task apply_style_def formats through."""
    class _Main:
        class _Page:
            client_id = 0
        page = _Page()
    main = _Main()

    def format_string(self, s):
        return s


class TestStyleFontNormalised(unittest.TestCase):
    def setUp(self):
        FrameContext.aspect_ratios[0] = Vec3(1024, 768, 0)
        FrameContext.context = types.SimpleNamespace(
            sbs=None, sim=None, event=types.SimpleNamespace(client_id=0))

    def tearDown(self):
        FrameContext.context = None

    def _apply(self, style):
        t = Text("t", "$text:`Hi`;")
        apply_style_def(StyleDefinition.parse(style), t, _Task())
        return t

    def test_leading_space_is_stripped(self):
        # The exact issue672 spelling.
        self.assertEqual(self._apply("font: gui-3;").default_font, "gui-3")

    def test_no_space_is_unchanged(self):
        self.assertEqual(self._apply("font:gui-3;").default_font, "gui-3")

    def test_trailing_space_is_stripped(self):
        self.assertEqual(self._apply("font:gui-3 ;").default_font, "gui-3")

    def test_alongside_other_props(self):
        t = self._apply("font: gui-3;col-width:content")
        self.assertEqual(t.default_font, "gui-3")
        self.assertIsNotNone(t.default_width)

    def test_click_font_also_stripped(self):
        t = self._apply("click_font: gui-2;")
        self.assertEqual(t.click_font, "gui-2")


if __name__ == "__main__":
    unittest.main()
