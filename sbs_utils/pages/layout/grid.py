"""Grid — an *additive* layout container.

The core layout math (``layout.py``) already distributes a Row's columns and a
Layout's rows. Grid doesn't touch that: it **composes the existing primitives**,
arranging cells into a fixed-column grid by emitting standard ``Row``s (each with
``columns`` cells) into a ``Layout``. The final row is padded with ``Hole``
spacers so columns stay aligned when the cell count isn't a multiple of the
column count.

Because it only builds Rows the engine already knows how to lay out, it adds no
new rendering path and can't regress existing layouts — a grid is just rows of
columns. Useful for editor surfaces: property grids, palettes, toolbars.

    grid = Grid(3, row_height="10px")
    for w in widgets:
        grid.add(w)
    grid.build(my_layout)      # appends the rows to an existing Layout
"""
from .row import Row
from .hole import Hole


class Grid:
    def __init__(self, columns, col_width=None, row_height=None):
        # At least one column; a 0/negative count would divide-by-zero below.
        self.columns = max(1, int(columns))
        self.col_width = col_width
        self.row_height = row_height
        self.cells = []

    def add(self, cell):
        """Append one cell (a Column/widget or nested Layout). Returns self."""
        self.cells.append(cell)
        return self

    def add_all(self, cells):
        for c in cells:
            self.add(c)
        return self

    def rows(self):
        """Build and return the grid's Rows without attaching them to a Layout.

        Real cells keep their own ``default_width``/height if already set; the
        grid's ``col_width``/``row_height`` are applied only as defaults. Short
        final rows are padded with ``Hole`` so the columns line up."""
        out = []
        for i in range(0, len(self.cells), self.columns):
            chunk = self.cells[i:i + self.columns]
            row = Row()
            if self.row_height is not None:
                row.set_row_height(self.row_height)
            for cell in chunk:
                if self.col_width is not None and getattr(cell, "default_width", None) is None:
                    cell.default_width = self.col_width
                row.add(cell)
            for _ in range(self.columns - len(chunk)):
                row.add(Hole())          # keep the last row's columns aligned
            out.append(row)
        return out

    def build(self, layout_item):
        """Append the grid's rows to an existing Layout. Returns the rows."""
        rows = self.rows()
        for row in rows:
            layout_item.add(row)
        return rows
