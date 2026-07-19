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
from sbs_utils.procedural.gui.table import _resolve_columns, _cell, _set, _widget_value, _disp


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

    # -- control cells --------------------------------------------------------
    def test_columns_carry_type_and_options(self):
        cols = _resolve_columns([{"a": True, "b": "x"}], [
            {"key": "a", "type": "checkbox", "width": 20},
            {"key": "b", "type": "dropdown", "options": ["x", "y"], "width": 80}],
            "gui-2")
        self.assertEqual(cols[0]["type"], "checkbox")
        self.assertEqual(cols[1]["type"], "dropdown")
        self.assertEqual(cols[1]["options"], ["x", "y"])

    def test_default_type_is_text(self):
        cols = _resolve_columns([{"a": "1"}], [{"key": "a", "width": 100}], "gui-2")
        self.assertEqual(cols[0]["type"], "text")

    def test_set_writes_back_to_dict(self):
        row = {"active": False}
        _set(row, "active", True)
        self.assertTrue(row["active"])

    def test_set_writes_back_to_object(self):
        class Row:
            pass
        r = Row()
        _set(r, "mode", "escort")
        self.assertEqual(r.mode, "escort")

    def test_disp_empty_becomes_space_but_zero_stays(self):
        # empty -> space (avoids the stray-backtick from `$text:``;`), but a
        # numeric 0 must NOT collapse to blank
        self.assertEqual(_disp(""), " ")
        self.assertEqual(_disp(None if False else ""), " ")
        self.assertEqual(_disp(0), "0")
        self.assertEqual(_disp("Mode"), "Mode")

    def test_widget_value_prefers_get_value(self):
        class W1:
            def get_value(self):
                return "got"
            value = "raw"
        self.assertEqual(_widget_value(W1()), "got")

        class W2:
            value = "raw"
        self.assertEqual(_widget_value(W2()), "raw")


if __name__ == "__main__":
    unittest.main()
