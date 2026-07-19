"""Grid container tests. Grid is an additive composer — it emits standard Rows
of Columns into a Layout and pads short rows with Hole spacers — so these check
the built structure (row/column counts, padding, size defaults, layout wiring)
without needing a renderer.
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest
from sbs_utils.pages.layout.grid import Grid
from sbs_utils.pages.layout.column import Column
from sbs_utils.pages.layout.hole import Hole
from sbs_utils.pages.layout.layout import Layout


def _cells(n):
    return [Column() for _ in range(n)]


class TestGrid(unittest.TestCase):
    def test_even_fill_no_padding(self):
        rows = Grid(3).add_all(_cells(6)).rows()
        self.assertEqual(len(rows), 2)
        for r in rows:
            self.assertEqual(len(r.columns), 3)
            self.assertFalse(any(isinstance(c, Hole) for c in r.columns))

    def test_short_last_row_padded_with_holes(self):
        rows = Grid(3).add_all(_cells(7)).rows()
        self.assertEqual(len(rows), 3)
        last = rows[-1].columns
        self.assertEqual(len(last), 3)                       # aligned
        self.assertEqual(sum(isinstance(c, Hole) for c in last), 2)   # 1 real + 2 holes
        self.assertFalse(isinstance(last[0], Hole))

    def test_single_column_is_a_stack(self):
        rows = Grid(1).add_all(_cells(4)).rows()
        self.assertEqual(len(rows), 4)
        self.assertTrue(all(len(r.columns) == 1 for r in rows))

    def test_zero_columns_coerced_to_one(self):
        g = Grid(0)
        self.assertEqual(g.columns, 1)

    def test_size_defaults_applied_but_not_overriding(self):
        preset = Column()
        preset.default_width = 42.0
        plain = Column()
        Grid(2, col_width=10.0, row_height="5px").add(preset).add(plain).rows()
        self.assertEqual(preset.default_width, 42.0)          # kept its own width
        self.assertEqual(plain.default_width, 10.0)           # got the grid default

    def test_row_height_applied(self):
        rows = Grid(2, row_height="5px").add_all(_cells(2)).rows()
        self.assertEqual(rows[0].default_height, "5px")

    def test_build_appends_to_layout(self):
        lay = Layout("g", None, 0, 0, 100, 50)
        before = len(lay.rows)
        rows = Grid(2).add_all(_cells(4)).build(lay)
        self.assertEqual(len(lay.rows), before + 2)
        self.assertEqual(lay.rows[-2:], rows)

    def test_empty_grid_builds_nothing(self):
        self.assertEqual(Grid(3).rows(), [])


if __name__ == "__main__":
    unittest.main()
