"""gui_list — a MAST-native, data-bound listbox whose row is a `with` block.

    with gui_list(ships, select=True) as ship:
        gui_text("{ship.name}")
        gui_button("Hail"):
            jump hail

The body is a *row template*: it runs once per item, not once. An ordinary
`with` can't express that (its body runs once), so ``PageList`` carries the
``_gui_row_template`` marker the `with` runtime keys on
(:mod:`sbs_utils.mast.core_nodes.with_cmd`): the runtime hands this object the
block's address (label + node range) and the ``as`` name, then skips the eager
run. This object builds a real ``LayoutListbox`` — so you get selection and
scrolling — and, whenever the listbox needs a row, **replays the captured block
for that item** into the listbox's sub-page, bounded by the block's ``WithEnd``.
"""
from ...helpers import FrameContext
from ..style import apply_control_styles
from ...pages.widgets.layout_listbox import LayoutListbox


class PageList:
    _gui_row_template = True          # the marker the `with` runtime keys on

    def __init__(self, items, style="", select=False, multi=False,
                 title=None, read_only=False):
        self.items = list(items) if items is not None else []
        self.style = style
        self.select = select
        self.multi = multi
        self.title = title
        self.read_only = read_only
        # filled in by _capture_block (the block's address) at build time
        self.task = None
        self.label = None
        self.start = 0
        self.end_node = None
        self.item_var = None
        self.listbox = None

    # Called by WithStartRuntimeNode with the captured block address.
    def _capture_block(self, task, label, start_loc, end_node, item_var):
        self.task = task                 # the gui task (shares scope with rows)
        self.label = label
        self.start = start_loc
        self.end_node = end_node
        self.item_var = item_var

    # Fired on the build pass: create the listbox and place it. The body was
    # skipped; the listbox will call _run_row per item at present time.
    def __enter__(self):
        page = FrameContext.page
        if page is None:
            return self
        tag = page.get_tag()
        self.listbox = LayoutListbox(
            0, 0, tag, self.items,
            item_template=self._run_row,
            title_template=self.title,
            section_style=None, title_section_style=None,
            select=self.select, multi=self.multi, carousel=False,
            collapsible=False, read_only=self.read_only)
        apply_control_styles(".listbox", self.style, self.listbox, self.task)
        page.add_content(self.listbox, None)
        return self

    def __exit__(self, ex=None, value=None, tb=None):
        return ex is None

    # The listbox's per-item template: run the captured block once for `item`,
    # building this row into the current sub-page (already FrameContext.page).
    def _run_row(self, item, **kwargs):
        task = self.task
        if task is None:
            return
        # Give the row a bounded height (like the default template) so the
        # listbox fits many rows; without it a row fills the box -> only 1 slot.
        from .row import gui_row
        gui_row("row-height: 1.0;")
        inputs = {"item": item, "LB_ITEM": item}
        if self.item_var:
            inputs[self.item_var] = item
        st = task.start_sub_task(self.label, inputs, defer=True, active_cmd=self.start)
        st._gui_row_end_node = self.end_node          # WithEnd stops the row here

        _page, _task = FrameContext.page, FrameContext.task
        FrameContext.task = st                         # keep page = the sub-page
        try:
            guard = 0
            while not st.active_ticker.done and guard < 100000:
                st.active_ticker.tick()
                guard += 1
        finally:
            FrameContext.page, FrameContext.task = _page, _task
            try:
                task.sub_tasks.remove(st)              # don't leak per-present rows
            except (ValueError, AttributeError):
                pass


def gui_list(items, style="", select=False, multi=False, title=None, read_only=False):
    """Data-bound listbox: the ``with`` block is the per-row template.

    Args:
        items: The rows to render. The ``as`` name (and ``item``) is bound to
            each one while the block runs.
        style (str, optional): listbox container style. Defaults to "".
        select (bool, optional): allow row selection. Defaults to False.
        multi (bool, optional): allow multiple selection. Defaults to False.
        title (str, optional): a title row for the listbox. Defaults to None.
        read_only (bool, optional): prevent modification. Defaults to False.

    Returns:
        PageList: A row-template context manager. Use with ``with``.

    Example:
        with gui_list(ships, select=True) as ship:
            gui_text("{ship.name}")
            gui_text("{ship.hull}%")
    """
    return PageList(items, style, select, multi, title, read_only)
