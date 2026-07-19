"""Repeater — an *additive* data-bound container.

Bind a list to a **child template**: for each item, ``factory(item, index)``
returns a cell (a Column/widget or nested Layout), and the Repeater lays the
cells out in ``columns``-wide rows. It builds on :class:`Grid`, so it emits only
standard Rows of Columns — no new render path.

    rep = Repeater(columns=1, factory=lambda ship, i: Text(f"s{i}", ship.name))
    rep.build(ships, my_layout)     # one row per ship, appended to the Layout

The fix for data-driven GUIs: author the template once, expand it per item at
runtime.
"""
from .grid import Grid


class Repeater:
    def __init__(self, columns=1, factory=None, col_width=None, row_height=None):
        self.columns = max(1, int(columns))
        self.factory = factory
        self.col_width = col_width
        self.row_height = row_height

    def cells_for(self, items):
        """Map items -> cells via the factory (called as ``factory(item, index)``)."""
        if self.factory is None:
            raise ValueError("Repeater needs a factory(item, index) -> cell")
        return [self.factory(item, i) for i, item in enumerate(items)]

    def rows_for(self, items):
        """Build the Rows for these items without attaching them to a Layout."""
        grid = Grid(self.columns, self.col_width, self.row_height)
        return grid.add_all(self.cells_for(items)).rows()

    def build(self, items, layout_item):
        """Append one template-expanded set of rows for ``items`` to a Layout."""
        rows = self.rows_for(items)
        for row in rows:
            layout_item.add(row)
        return rows
