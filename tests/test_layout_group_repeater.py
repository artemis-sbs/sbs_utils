"""Group/Panel and Repeater container tests. Both are additive composers over
the standard Layout/Row/Column primitives, so these check the built structure
(title row, border config, per-item rows, factory wiring) without a renderer.
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest
from sbs_utils.pages.layout.group import Group
from sbs_utils.pages.layout.repeater import Repeater
from sbs_utils.pages.layout.column import Column
from sbs_utils.pages.layout.text import Text
from sbs_utils.pages.layout.hole import Hole


class TestGroup(unittest.TestCase):
    def test_titled_group_has_title_row(self):
        g = Group("sensors", title="Sensors")
        self.assertEqual(len(g.layout.rows), 1)              # just the title so far
        title = g.title_row
        self.assertIsNotNone(title)
        self.assertEqual(len(title.columns), 1)
        self.assertIsInstance(title.columns[0], Text)
        self.assertEqual(title.columns[0].tag, "sensors:title")
        self.assertEqual(title.default_height, 6.0)          # off the flex share

    def test_untitled_group_is_plain_layout(self):
        g = Group("plain", title=None)
        self.assertEqual(len(g.layout.rows), 0)
        self.assertIsNone(g.title_row)

    def test_border_applied(self):
        g = Group("bord", title=None, border_color="#f80", border_style="2px")
        self.assertEqual(g.layout.border_color, "#f80")
        self.assertEqual(g.layout.border_style, "2px")

    def test_no_border_when_color_none(self):
        g = Group("nb", title=None, border_color=None)
        self.assertIsNone(g.layout.border_color)

    def test_add_content_rows_after_title(self):
        from sbs_utils.pages.layout.row import Row
        g = Group("g", title="T")
        r = Row(); r.add(Column())
        g.add(r)
        self.assertEqual(len(g.layout.rows), 2)              # title + content
        self.assertIs(g.layout.rows[-1], r)
        self.assertIs(g.build(), g.layout)


class TestRepeater(unittest.TestCase):
    def test_one_row_per_item_single_column(self):
        items = ["a", "b", "c"]
        rep = Repeater(columns=1, factory=lambda it, i: Text(f"t{i}", it))
        rows = rep.rows_for(items)
        self.assertEqual(len(rows), 3)
        self.assertTrue(all(len(r.columns) == 1 for r in rows))
        self.assertEqual(rows[0].columns[0].tag, "t0")

    def test_factory_receives_index(self):
        seen = []
        rep = Repeater(columns=1, factory=lambda it, i: (seen.append((it, i)), Column())[1])
        rep.cells_for(["x", "y"])
        self.assertEqual(seen, [("x", 0), ("y", 1)])

    def test_multi_column_pads_last_row(self):
        rep = Repeater(columns=3, factory=lambda it, i: Column())
        rows = rep.rows_for(range(4))
        self.assertEqual(len(rows), 2)
        self.assertEqual(sum(isinstance(c, Hole) for c in rows[-1].columns), 2)

    def test_build_appends_to_layout(self):
        from sbs_utils.pages.layout.layout import Layout
        lay = Layout("r", None, 0, 0, 100, 50)
        rep = Repeater(columns=1, factory=lambda it, i: Column())
        rows = rep.build([1, 2], lay)
        self.assertEqual(len(lay.rows), 2)
        self.assertEqual(lay.rows, rows)

    def test_missing_factory_raises(self):
        with self.assertRaises(ValueError):
            Repeater(columns=1).cells_for([1, 2])


if __name__ == "__main__":
    unittest.main()
