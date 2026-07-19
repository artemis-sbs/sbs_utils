from ...helpers import FrameContext


class PageGrid:
    """Context manager returned by :func:`gui_grid`. While the ``with`` block is
    open, every GUI item you add flows into an ``columns``-wide grid — a new row
    starts automatically after every ``columns`` items, and the final row is
    padded so the columns line up. Nestable, like ``gui_sub_section``."""

    def __init__(self, columns):
        self.columns = columns
        self.page = FrameContext.page

    def __enter__(self):
        if self.page is not None:
            self.page.grid_begin(self.columns)
        return self

    # MAST's `with` calls __exit__ with a single arg; Python passes three. Accept
    # both (see PageSubSection).
    def __exit__(self, ex=None, value=None, tb=None):
        if self.page is not None:
            self.page.grid_end()
        return ex is None


def gui_grid(columns=1):
    """Lay the GUI items you add next out as a grid, as a context manager.

    Inside the ``with`` block, items flow left-to-right and wrap to a new row
    every ``columns`` items — no manual ``gui_row()`` needed. The short final
    row is padded so columns stay aligned. Because it only starts standard rows,
    it adds no new rendering path.

    Args:
        columns (int): Number of columns (cells per row). Minimum 1.

    Returns:
        PageGrid: Context manager. Use with ``with``.

    Example:
        with gui_grid(3):
            gui_text("Name")
            gui_text("Side")
            gui_text("Status")
            for ship in ships:
                gui_text(ship.name)
                gui_text(ship.side)
                gui_text(ship.status)
    """
    return PageGrid(columns)
