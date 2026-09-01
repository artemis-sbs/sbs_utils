"""gui_grid() tests. gui_grid is a MAST-native container: `with gui_grid(N):`
puts the page into auto-flow mode so each added item wraps to a new row every N,
with the final row Hole-padded. These drive the page's grid_begin/add_content/
grid_end directly (what the gui_* calls do) and the PageGrid context manager,
without a renderer.
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest
import cosmos_dev.mock.sbs as sbs          # registers the bare `sbs` shim
from sbs_utils.mast_sbs.maststorypage import StoryPage
from sbs_utils.pages.layout.column import Column
from sbs_utils.pages.layout.hole import Hole
from sbs_utils.procedural.gui.grid import gui_grid, PageGrid
from sbs_utils.helpers import FrameContext


def _new_page():
    page = StoryPage()
    page.pending_gui = False          # skip on_new_gui() wiring in add_tag
    return page


def _fill(page, n):
    for i in range(n):
        c = Column()
        c.tag = f"c{i}"
        page.add_content(c, None)


def _grid_rows(page):
    return page.pending_layouts[-1].rows


class TestGuiGridAutoFlow(unittest.TestCase):
    def test_wraps_every_n_and_pads_last_row(self):
        page = _new_page()
        page.grid_begin(3)
        _fill(page, 7)
        page.grid_end()
        rows = _grid_rows(page)
        self.assertEqual([len(r.columns) for r in rows], [3, 3, 3])
        self.assertEqual(sum(isinstance(c, Hole) for c in rows[-1].columns), 2)
        self.assertEqual(rows[0].columns[0].tag, "c0")

    def test_exact_multiple_has_no_trailing_empty_row(self):
        page = _new_page()
        page.grid_begin(3)
        _fill(page, 6)
        page.grid_end()
        rows = _grid_rows(page)
        self.assertEqual([len(r.columns) for r in rows], [3, 3])   # no [.. , 0]

    def test_single_column_stacks(self):
        page = _new_page()
        page.grid_begin(1)
        _fill(page, 4)
        page.grid_end()
        rows = _grid_rows(page)
        self.assertEqual([len(r.columns) for r in rows], [1, 1, 1, 1])

    def test_columns_coerced_to_min_one(self):
        page = _new_page()
        page.grid_begin(0)
        _fill(page, 2)
        page.grid_end()
        rows = _grid_rows(page)
        self.assertEqual([len(r.columns) for r in rows], [1, 1])

    def test_content_after_grid_is_not_in_grid_row(self):
        page = _new_page()
        page.grid_begin(2)
        _fill(page, 2)                # fills row -> auto-breaks to fresh row
        page.grid_end()
        # a plain item after the grid lands on its own row, ungridded
        after = Column(); after.tag = "after"
        page.add_content(after, None)
        page.add_row()                # flush
        rows = _grid_rows(page)
        self.assertEqual(len(rows[0].columns), 2)
        self.assertEqual(rows[-1].columns[-1].tag, "after")
        self.assertFalse(page._grid_stack)   # grid closed


class TestPageGridContextManager(unittest.TestCase):
    def test_with_block_opens_and_closes(self):
        page = _new_page()
        FrameContext.page = page
        try:
            with gui_grid(2):
                _fill(page, 3)
            self.assertFalse(page._grid_stack)      # __exit__ closed it
            rows = _grid_rows(page)
            self.assertEqual(len(rows[0].columns), 2)
            self.assertEqual(sum(isinstance(c, Hole) for c in rows[-1].columns), 1)
        finally:
            FrameContext.page = None

    def test_mast_style_single_arg_exit(self):
        # MAST calls __exit__ with one arg; Python with three. Both must work.
        page = _new_page()
        pg = PageGrid(2)
        pg.page = page
        pg.__enter__()
        _fill(page, 1)
        self.assertTrue(pg.__exit__(None))          # single-arg (MAST) form
        self.assertFalse(page._grid_stack)

    def test_nested_grids(self):
        page = _new_page()
        page.grid_begin(2)
        _fill(page, 1)
        page.grid_begin(3)          # nested
        _fill(page, 3)
        page.grid_end()
        self.assertEqual(len(page._grid_stack), 1)  # back to outer
        page.grid_end()
        self.assertFalse(page._grid_stack)


if __name__ == "__main__":
    unittest.main()

class TestGridOfSubSections(unittest.TestCase):
    """A grid counts CELLS, not everything a cell builds inside itself.

    The counter used to run on every add_content while a grid was open. A sub-section
    is added to its parent row when it POPS, not through add_content, so a grid of
    sub-sections counted their CONTENTS instead - and broke rows in the middle of
    them. Three tiles of icon+title+description in a 4-column grid put the second
    tile's icon on cell 4, so that tile alone got a row break between its icon and its
    own title. It read as "one icon paints differently from the others" (ePADD, first
    engine screenshot).
    """

    def _tile(self, page, widgets):
        # PageSubSection reads FrameContext.page at construction.
        from sbs_utils.procedural.gui.section import PageSubSection
        FrameContext.page = page
        self.addCleanup(setattr, FrameContext, "page", None)
        sub = PageSubSection(None)
        sub.__enter__()
        for i in range(widgets):
            c = Column()
            c.tag = f"w{i}"
            page.add_content(c, None)
        sub.__exit__()
        return sub

    def test_three_tiles_of_three_widgets_are_three_cells_in_one_row(self):
        page = _new_page()
        page.grid_begin(4)
        for _ in range(3):
            self._tile(page, 3)          # 9 inner widgets - none of them are cells
        page.grid_end()
        rows = _grid_rows(page)
        self.assertEqual(len(rows), 1, "the tiles are one row of cells")
        self.assertEqual(len(rows[0].columns), 4, "3 tiles + 1 Hole of padding")

    def test_every_tile_keeps_its_own_shape(self):
        """The actual symptom: one tile had an extra row and the others did not."""
        page = _new_page()
        page.grid_begin(4)
        for _ in range(3):
            self._tile(page, 3)
        page.grid_end()
        tiles = [c for c in _grid_rows(page)[0].columns if not isinstance(c, Hole)]
        shapes = [len(t.rows) for t in tiles]
        self.assertEqual(len(set(shapes)), 1,
                         f"tiles disagree on how many rows they have: {shapes}")

    def test_a_grid_of_plain_widgets_is_unchanged(self):
        """The ordinary case has to keep working exactly as it did."""
        page = _new_page()
        page.grid_begin(3)
        _fill(page, 7)
        page.grid_end()
        rows = _grid_rows(page)
        self.assertEqual([len(r.columns) for r in rows], [3, 3, 3])

    def test_cells_still_wrap_when_there_are_more_than_fit(self):
        page = _new_page()
        page.grid_begin(2)
        for _ in range(5):
            self._tile(page, 2)
        page.grid_end()
        rows = [r for r in _grid_rows(page) if r.columns]
        self.assertEqual([len(r.columns) for r in rows], [2, 2, 2])

class _Main:
    def __init__(self, page):
        self.page = page


class _StyleTask:
    """Style parsing reaches the client through `task.main.page.client_id`."""

    def __init__(self, page):
        self.main = _Main(page)

    def compile_and_format_string(self, s):
        return s

    def format_string(self, s):
        return s


def _styled_page():
    page = _new_page()
    page.client_id = 1
    page.gui_task = _StyleTask(page)
    return page


class TestGridRowStyle(unittest.TestCase):
    """A grid makes its own rows, so `row_style` is the only way to size them."""

    def test_the_style_reaches_every_row_the_grid_starts(self):
        page = _styled_page()
        page.grid_begin(2, "row-height: content;")
        _fill(page, 4)
        page.grid_end()
        rows = [r for r in _grid_rows(page) if r.columns]
        self.assertEqual(len(rows), 2)
        for r in rows:
            self.assertEqual(str(getattr(r, "default_height", None)),
                             "ContentSize(content)")

    def test_no_style_leaves_rows_alone(self):
        page = _styled_page()
        page.grid_begin(2)
        _fill(page, 2)
        page.grid_end()
        row = [r for r in _grid_rows(page) if r.columns][0]
        self.assertNotEqual(str(getattr(row, "default_height", None)),
                            "ContentSize(content)")
