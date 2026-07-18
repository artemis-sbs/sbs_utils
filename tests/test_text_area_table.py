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
from sbs_utils.pages.layout.text_area import TextArea, TableLine
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


if __name__ == "__main__":
    unittest.main()
