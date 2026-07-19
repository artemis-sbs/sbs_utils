"""gui_table — declarative table over gui_list_box.

Tests the column-sizing logic (the value-add a per-row template can't do): auto
columns measured across all rows, normalized to fill the row and share space the
fixed columns leave.
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest

from cosmos_dev.mock import sbs
from sbs_utils.helpers import FrameContext, Context, FakeEvent
from sbs_utils.procedural.gui.table import _resolve_columns, _cell


class TestGuiTable(unittest.TestCase):
    def setUp(self):
        sbs.create_new_sim()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent())

    def test_cell_reads_dict_and_object(self):
        self.assertEqual(_cell({"name": "Artemis"}, "name"), "Artemis")

        class Row:
            pass
        r = Row()
        r.name = "Intrepid"
        self.assertEqual(_cell(r, "name"), "Intrepid")
        self.assertEqual(_cell({"a": 1}, "missing"), "")

    def test_all_auto_widths_fill_the_row(self):
        items = [{"name": "Artemis", "hp": 100, "side": "tsn"},
                 {"name": "Intrepid", "hp": 85, "side": "tsn"}]
        cols = _resolve_columns(items, [
            {"key": "name", "label": "Ship"},
            {"key": "hp", "label": "Hull"},
            {"key": "side", "label": "Side"}], "gui-2")
        self.assertAlmostEqual(sum(c["width"] for c in cols), 100.0, delta=0.5)

    def test_fixed_column_kept_auto_takes_remainder(self):
        items = [{"name": "Artemis", "side": "tsn"}]
        cols = _resolve_columns(items, [
            {"key": "name", "label": "Ship"},               # auto
            {"key": "side", "label": "Side", "width": 30}], "gui-2")
        self.assertEqual(cols[1]["width"], 30)
        self.assertAlmostEqual(cols[0]["width"], 70.0, delta=0.5)

    def test_wider_content_gets_more_width(self):
        items = [{"a": "x", "b": "a considerably longer value"}]
        cols = _resolve_columns(items, [{"key": "a"}, {"key": "b"}], "gui-2")
        self.assertGreater(cols[1]["width"], cols[0]["width"])

    def test_header_counts_toward_auto_width(self):
        # a wide header with short data still reserves room for the header
        items = [{"x": "1"}]
        cols = _resolve_columns(items, [
            {"key": "x", "label": "A Very Wide Header"},
            {"key": "y", "label": "Y", "width": 10}], "gui-2")
        self.assertAlmostEqual(cols[0]["width"], 90.0, delta=0.5)

    def test_alignment_mapping(self):
        cols = _resolve_columns([{"x": "1"}], [
            {"key": "x", "align": "r", "width": 100}], "gui-2")
        self.assertEqual(cols[0]["just"], "right")


if __name__ == "__main__":
    unittest.main()
