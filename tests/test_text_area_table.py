"""TableLine: GFM pipe tables in gui_text_area (gui-sizing-accuracy).

Verifies the block parses, sizes columns to fit the region width (no horizontal
overflow — there's no h-scroll), reads per-column alignment, and doesn't mistake
prose for a table.
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest

from cosmos_dev.mock import sbs
from sbs_utils.helpers import FrameContext, Context, FakeEvent
from sbs_utils.gui import get_client_aspect_ratio
from sbs_utils.pages.layout.text_area import TextArea, TableLine, LinkLine, HrLine, TextLine
from sbs_utils.pages.layout.layout import Bounds


class TestTextAreaTable(unittest.TestCase):
    def setUp(self):
        sbs.create_new_sim()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent())

    def _calc(self, text, area=(0, 0, 80, 60)):
        ta = TextArea("t", text)
        ta.bounds = Bounds(*area)
        ta.calc_rich(0)
        return ta

    def _tables(self, ta):
        return [ln for ln in ta.lines if isinstance(ln, TableLine)]

    def test_table_parsed_as_block(self):
        md = ("| Ship | HP | Side |\n"
              "|:--|:--:|--:|\n"
              "| Artemis | 100 | tsn |\n"
              "| Intrepid | 85 | tsn |")
        tables = self._tables(self._calc(md))
        self.assertEqual(len(tables), 1)
        t = tables[0]
        self.assertEqual(t.ncols, 3)
        self.assertEqual(len(t.rows), 3)          # header + 2 data (separator dropped)
        self.assertEqual(t.aligns, ["l", "c", "r"])
        self.assertGreater(t.height, 0)

    def test_columns_fit_region_width(self):
        # long cells must be shrunk so columns + gutters never exceed the region px
        md = ("| A | B | C |\n|--|--|--|\n"
              "| xxxxxxxxxxxxxxx | yyyyyyyyyyyyyyy | zzzzzzzzzzzzzzz |")
        ta = self._calc(md)
        t = self._tables(ta)[0]
        arv = get_client_aspect_ratio(0)
        pixel_width = (ta.bounds.right - ta.bounds.left) / 100 * arv.x
        total = sum(t.col_px) + t.cell_pad_px * (t.ncols - 1)
        self.assertLessEqual(total, pixel_width + 1.0)

    def test_lone_pipe_line_is_prose(self):
        ta = self._calc("| just prose that happens to start with a pipe")
        self.assertEqual(self._tables(ta), [])

    def test_table_without_separator(self):
        ta = self._calc("| a | b |\n| c | d |")
        t = self._tables(ta)
        self.assertEqual(len(t), 1)
        self.assertEqual(t[0].aligns, [])          # all default-left
        self.assertEqual(len(t[0].rows), 2)

    def test_text_around_table_preserved(self):
        md = ("# Fleet\n"
              "| Ship | HP |\n|--|--|\n| Artemis | 100 |\n"
              "After the table.")
        ta = self._calc(md)
        self.assertEqual(len(self._tables(ta)), 1)
        # heading + table + trailing text all present as lines
        self.assertGreaterEqual(len(ta.lines), 3)


class TestTextAreaLinksAndRule(unittest.TestCase):
    def setUp(self):
        sbs.create_new_sim()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent())

    def _calc(self, text):
        ta = TextArea("t", text)
        ta.bounds = Bounds(0, 0, 80, 60)
        ta.calc_rich(0)
        return ta

    def test_whole_line_link_parsed(self):
        ta = self._calc("Enemies:\n[Torgoth](ref://torgoth)")
        links = [ln for ln in ta.lines if isinstance(ln, LinkLine)]
        self.assertEqual(len(links), 1)
        self.assertEqual(links[0].display, "Torgoth")
        # the click_tag is registered -> key for on_message to resolve
        self.assertIn(links[0].click_tag, ta._link_map)
        self.assertEqual(ta._link_map[links[0].click_tag], "torgoth")

    def test_link_click_navigates_via_resolver(self):
        ta = self._calc("Enemies:\n[Torgoth](ref://torgoth)")
        ctag = [ln for ln in ta.lines if isinstance(ln, LinkLine)][0].click_tag
        ta.link_resolver = lambda key: f"# {key.title()}\nDetails about the {key}."
        ta.present = lambda event: None            # isolate nav from the render path
        ta.on_message(FakeEvent(sub_tag=ctag))
        self.assertIn("torgoth", " ".join(ta.content).lower())

    def test_link_callback_fires(self):
        ta = self._calc("Enemies:\n[Torgoth](ref://torgoth)")
        ctag = [ln for ln in ta.lines if isinstance(ln, LinkLine)][0].click_tag
        seen = []
        ta.on_link_cb = lambda key, sender: seen.append(key)
        ta.on_message(FakeEvent(sub_tag=ctag))
        self.assertEqual(seen, ["torgoth"])

    def test_prose_link_not_whole_line_is_text(self):
        # inline (not whole-line) link is left as text for now, not a LinkLine
        ta = self._calc("See [Torgoth](ref://torgoth) for details")
        self.assertEqual([ln for ln in ta.lines if isinstance(ln, LinkLine)], [])

    def test_hr_rule(self):
        ta = self._calc("Above\n<hr>\nBelow")
        self.assertEqual(len([ln for ln in ta.lines if isinstance(ln, HrLine)]), 1)

    def test_dashes_still_table_separator_not_hr(self):
        # '---' must remain a table separator, never an <hr>
        ta = self._calc("| a | b |\n|---|---|\n| 1 | 2 |")
        self.assertEqual(len([ln for ln in ta.lines if isinstance(ln, HrLine)]), 0)
        self.assertEqual(len([ln for ln in ta.lines if isinstance(ln, TableLine)]), 1)


class TestTextAreaLineBreak(unittest.TestCase):
    """`<br>` is a break EVERYWHERE, including inside a list.

    A <br> between numbered items used to inherit the list style, get the list's
    prepend glued on, and reach the reader as the literal text "1<br>" -- LM's
    "How a build works" help topic is written that way throughout.
    """
    def setUp(self):
        sbs.create_new_sim()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent())

    def _texts(self, text):
        ta = TextArea("t", text)
        ta.bounds = Bounds(0, 0, 80, 60)
        ta.calc_rich(0)
        return [ln.text for ln in ta.lines if isinstance(ln, TextLine)]

    def test_br_in_prose_is_a_break(self):
        # `^` is what the engine reads as a newline
        self.assertEqual(self._texts("Above\n<br>\nBelow"), ["Above", "^", "Below"])

    def test_br_between_list_items_is_a_break(self):
        got = self._texts("1. GATHER\n<br>\n2. FABRICATE\n<br>\n3. DELIVER")
        self.assertEqual([t for t in got if t == "^"], ["^", "^"])
        self.assertFalse([t for t in got if "<br>" in t],
                         f"a <br> reached the reader as literal text: {got}")

    def test_br_does_not_disturb_the_numbering(self):
        got = self._texts("1. GATHER\n<br>\n2. FABRICATE\n<br>\n3. DELIVER")
        numbered = [t for t in got if t != "^"]
        self.assertEqual([t[:2] for t in numbered], ["1.", "2.", "3."])

    def test_self_closing_and_case(self):
        self.assertEqual(self._texts("a\n<BR/>\nb"), ["a", "^", "b"])

class TestTextAreaListMarkers(unittest.TestCase):
    """A generated marker is separated from the text it marks.

    get_line_style eats the line's own "1. " / "- ", so the marker the renderer
    puts back has to supply the space itself - otherwise every list in every
    document reads "1.GATHER the materials", "-Helm".
    """
    def setUp(self):
        sbs.create_new_sim()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent())

    def _texts(self, text):
        ta = TextArea("t", text)
        ta.bounds = Bounds(0, 0, 80, 60)
        ta.calc_rich(0)
        return [ln.text for ln in ta.lines if isinstance(ln, TextLine)]

    def test_ordered_marker_has_a_space(self):
        got = self._texts("1. GATHER the materials\n2. FABRICATE it")
        self.assertEqual(got, ["1. GATHER the materials", "2. FABRICATE it"])

    def test_bullet_marker_has_a_space(self):
        self.assertEqual(self._texts("- Helm\n- Weapons"), ["- Helm", "- Weapons"])

    def test_author_numbering_is_still_replaced_not_doubled(self):
        # the author's own "7." is dropped; the renderer numbers the list
        self.assertEqual(self._texts("7. seven\n9. nine"), ["1. seven", "2. nine"])

    def test_unmarked_styles_gain_no_space(self):
        # a heading has no prepend, so nothing is inserted in front of it
        # (two lines: a one-line text area takes the simple, non-markdown path)
        self.assertEqual(self._texts("# Fabrication\nprose"), ["Fabrication", "prose"])


if __name__ == "__main__":
    unittest.main()
