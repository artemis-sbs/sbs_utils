"""gui_list — a MAST-native, data-bound list whose row is a `with` block.

    with gui_list(ships) as ship:
        gui_text("{ship.name}")
        gui_button("Hail"):
            jump hail

Unlike an ordinary `with`, the body here is a *row template*: it runs once per
item, not once. The ``_gui_row_template`` marker tells the `with` runtime
(:mod:`sbs_utils.mast.core_nodes.with_cmd`) to drive the block like a ``for``
loop — running the body once per item, on this task, binding the ``as`` name to
each row — so the row's ``gui_*`` calls build that row. A fresh layout row is
started for each item, so several widgets in the block become that row's cells.

v1 builds each item as plain rows in the current layout (a data-bound repeater).
Selection/scroll (a real listbox) layer on next.
"""


class PageList:
    _gui_row_template = True          # the marker the `with` runtime keys on

    def __init__(self, items):
        self.items = list(items) if items is not None else []

    # The `with` runtime iterates this to drive the per-row loop.
    def row_items(self):
        return self.items

    # Called by the runtime as each row begins, before the body runs.
    def on_row(self, item):
        from .row import gui_row
        gui_row()                     # each item gets its own row; body = its cells

    def __enter__(self):
        return self

    def __exit__(self, ex=None, value=None, tb=None):
        return ex is None


def gui_list(items):
    """Data-bound list: the ``with`` block is the per-row template.

    Args:
        items: The rows to render. The ``as`` name is bound to each one while
            the block runs.

    Returns:
        PageList: A row-template context manager. Use with ``with``.

    Example:
        with gui_list(ships) as ship:
            gui_text("{ship.name}")
            gui_text("{ship.hull}%")
    """
    return PageList(items)
