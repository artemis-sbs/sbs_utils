from sbs_utils.helpers import FrameContext
from sbs_utils.pages.widgets.layout_listbox import LayoutListbox
def apply_control_styles (control_name, extra_style, layout_item, task):
    """Apply a named control style and optional overrides to a layout item.
    
    ``extra_style`` may be a raw CSS-style string (``"key:value;..."``) or
    a style name. It is applied on top of the base ``control_name`` style.
    
    Args:
        control_name (str): Base control style name.
        extra_style (str | dict | None): Additional style string, name, or
            parsed dict applied after the base style.
        layout_item (LayoutItem): Layout item to receive the style.
        task (MastAsyncTask): GUI task used for string formatting."""
def gui_list (items, style='', select=False, multi=False, title=None, read_only=False, row_height='1.6em'):
    """Data-bound listbox: the ``with`` block is the per-row template.
    
    Args:
        items: The rows to render. The ``as`` name (and ``item``) is bound to
            each one while the block runs.
        style (str, optional): listbox container style. Defaults to "".
        select (bool, optional): allow row selection. Defaults to False.
        multi (bool, optional): allow multiple selection. Defaults to False.
        title (str, optional): a title row for the listbox. Defaults to None.
        read_only (bool, optional): prevent modification. Defaults to False.
        row_height (str, optional): height of each row (e.g. "1.6em", "3em").
            A roomier value gives cells more breathing room. Defaults to "1.6em".
    
    Returns:
        PageList: A row-template context manager. Use with ``with``.
    
    Example:
        with gui_list(ships, select=True) as ship:
            gui_text("{ship.name}")
            gui_text("{ship.hull}%")"""
class PageList(object):
    """class PageList"""
    def __enter__ (self):
        ...
    def __exit__ (self, ex=None, value=None, tb=None):
        ...
    def __init__ (self, items, style='', select=False, multi=False, title=None, read_only=False, row_height='1.6em'):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def _capture_block (self, task, label, start_loc, end_node, item_var):
        ...
    def _run_row (self, item, **kwargs):
        ...
    def get_selected (self):
        ...
    def get_selected_index (self):
        ...
    def select_all (self):
        ...
    @property
    def selected (self):
        ...
    def set_selected_index (self, index, set_cur=True):
        ...
class PageTable(PageList):
    """``with gui_table(items, headers=[...]) as row:`` — a selectable, scrolling
    table whose **row you author as a block** (like ``gui_list``), with an aligned
    header built from ``headers``. Each widget in the block is a column; the header
    labels line up above them (equal-flex columns). Reuses the row-template
    machinery of :class:`PageList`."""
    def __enter__ (self):
        ...
    def __init__ (self, items, headers=None, style='', select=False, multi=False, read_only=False, row_height='1.6em'):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def _header_row (self, **kwargs):
        ...
