"""A one-line `![](ns://urn)` must not take the simple-text fast path.

The bug this pins: `TextArea.value` short-circuits a single line with no newline into
`simple_text`, which emits it as ONE `send_gui_text` and never runs the markdown rules. So a
text area whose whole content is an embed - `![](face://ter #fff 0 0;)`, `![](image://key)` -
drew its own markup as a wall of characters instead of the picture.

Silent, and it looked like the markdown was unsupported rather than unparsed. This file's own
docstring example (`gui_text_area("![](image://logo?scale=0.5) Mission active")`) is one line,
so the DOCUMENTED form was the broken one.

Only an `ns://urn` disqualifies the fast path. `RE_LINK_REF` has every group optional and
matches nearly any line, so a bare `[...]` must not be enough - and a heading or a bullet on
one line still reads fine as text, which is what the fast path is for.

    python -m unittest tests.test_text_area_embed
"""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import sbs_utils.mast_sbs.story_nodes  # import first to break a circular import
from cosmos_dev.mock import sbs
from sbs_utils.helpers import FrameContext, Context, FakeEvent
from sbs_utils.pages.layout.text_area import TextArea, FaceLine, ImageLine

FACE = "ter #ffffff 6 0 6 -2;ter #fff 1 4;"


class TestEmbedTakesTheRichPath(unittest.TestCase):
    def setUp(self):
        sbs.create_new_sim()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent())

    def area(self, text):
        return TextArea("t", text)

    def test_a_lone_face_embed_is_not_simple_text(self):
        self.assertFalse(self.area(f"![](face://{FACE}?height=88&align=center)").simple_text)

    def test_a_lone_image_embed_is_not_simple_text(self):
        self.assertFalse(self.area("![](image://crew:tng:data?scale=1)").simple_text)

    def test_a_lone_ship_embed_is_not_simple_text(self):
        self.assertFalse(self.area("![](ship://tsn_light_cruiser?height=40)").simple_text)

    def test_the_documented_one_line_example_is_not_simple_text(self):
        self.assertFalse(self.area("![](image://logo?scale=0.5) Mission active").simple_text)

    def test_a_link_DEFINITION_on_its_own_is_not_simple_text(self):
        self.assertFalse(self.area("![logo]: image://logo").simple_text)

    def test_markdown_off_keeps_the_fast_path(self):
        # Nothing is going to parse it, so there is nothing to promote it for.
        ta = TextArea("t", f"![](face://{FACE})", markdown=False)
        self.assertTrue(ta.simple_text)


class TestOrdinaryTextStillTakesTheFastPath(unittest.TestCase):
    """The fast path is the common case and must keep it - this is not a licence to
    promote everything."""

    def setUp(self):
        sbs.create_new_sim()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent())

    def test_plain_text(self):
        self.assertTrue(TextArea("t", "All systems nominal.").simple_text)

    def test_a_property_string(self):
        self.assertTrue(TextArea("t", "$text:`hello`;").simple_text)

    def test_a_heading(self):
        self.assertTrue(TextArea("t", "## Status").simple_text)

    def test_a_bracket_that_is_not_an_embed(self):
        # `[warp core]` is prose. RE_LINK_REF matches it; no `ns` means no embed.
        self.assertTrue(TextArea("t", "Check the [warp core] readings").simple_text)


class TestTheEmbedActuallyRenders(unittest.TestCase):
    """Promotion is only half of it - the rich path has to produce the widget."""

    def setUp(self):
        sbs.create_new_sim()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent())

    def parsed(self, text):
        ta = TextArea("t", text)
        ta.bounds.left, ta.bounds.top, ta.bounds.right, ta.bounds.bottom = 0, 0, 100, 100
        ta.calc_rich(0)
        return ta.lines

    def test_a_face_embed_becomes_a_FaceLine_carrying_the_face_string(self):
        lines = self.parsed(f"![](face://{FACE}?height=88&align=center)")
        self.assertEqual([type(l).__name__ for l in lines], ["FaceLine"])
        self.assertIsInstance(lines[0], FaceLine)
        self.assertEqual(lines[0].text, FACE)
        self.assertEqual(lines[0].align, "center")

    def test_an_image_embed_becomes_an_ImageLine(self):
        lines = self.parsed("![](image://crew:tng:data?scale=1&fill=center)")
        self.assertEqual([type(l).__name__ for l in lines], ["ImageLine"])
        self.assertIsInstance(lines[0], ImageLine)


if __name__ == "__main__":
    unittest.main()
