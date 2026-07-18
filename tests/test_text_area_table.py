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
from sbs_utils.pages.layout.text_area import TextArea, TableLine, LinkLine, HrLine
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


if __name__ == "__main__":
    unittest.main()
