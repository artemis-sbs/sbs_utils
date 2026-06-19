from sbs_utils.helpers import FrameContext
from sbs_utils.pages.widgets.layout_listbox import LayoutListBoxHeader
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
def gui_list_box (items, style, item_template=None, title_template=None, section_style=None, title_section_style=None, select=False, multi=False, carousel=False, collapsible=False, read_only=False):
    """Add a listbox to the current GUI layout.
    
    Args:
        items (list): Items to display. Plain strings render as text rows;
            ``LayoutListBoxHeader`` objects (from ``gui_list_box_header``)
            render as collapsible section dividers.
        style (str): CSS-like style overrides for the listbox container.
        item_template (callable | None, optional): Called per item to build
            its row layout. Defaults to None (built-in text row).
        title_template (str | callable | None, optional): Title for the
            listbox. A string is used as-is; a callable is invoked to build
            the title row. Defaults to None.
        section_style (str | None, optional): Style overrides applied to each
            item row section. Defaults to None.
        title_section_style (str | None, optional): Style overrides applied to
            the title section. Defaults to None.
        select (bool, optional): Allow item selection. Defaults to ``False``.
        multi (bool, optional): Allow multiple simultaneous selections. Only
            used when ``select=True``. Defaults to ``False``.
        carousel (bool, optional): Use carousel styling (e.g. ship-type
            selection). Defaults to ``False``.
        collapsible (bool, optional): Clicking a header collapses items until
            the next header. Defaults to ``False``.
        read_only (bool, optional): Prevent item modification. Defaults to
            ``False``.
    
    Returns:
        LayoutListbox: The layout object created.
    
    Example:
        gui_list_box(items, style="area:0,0,100,100;", select=True)"""
def gui_list_box_header (label, collapse=False, indent=0, selectable=False, data=None, visual_indent=None):
    """Create a collapsible section header for use in a listbox.
    
    When ``collapsible=True`` is set on the listbox, clicking a header toggles
    the visibility of items that follow it until the next header.
    
    Args:
        label (str): Header label text.
        collapse (bool, optional): Start in collapsed state. Defaults to
            ``False``.
        indent (int, optional): Logical indent level for tree structures.
            Defaults to 0.
        selectable (bool, optional): Whether clicking the header fires a
            selection event in addition to toggling collapse. Defaults to
            ``False``.
        data (object, optional): Arbitrary data attached to the header item.
            Defaults to None.
        visual_indent (int | None, optional): Override indent level for
            rendering only. Defaults to None (uses ``indent``).
    
    Returns:
        LayoutListBoxHeader: The header item."""
def gui_list_box_is_header (item):
    """Return whether a listbox item is a collapsible header.
    
    Args:
        item: Any item from a listbox items list.
    
    Returns:
        bool: ``True`` if the item is a ``LayoutListBoxHeader``.
    
    Example:
        for item in items:
            if gui_list_box_is_header(item):
                ~~ print("header:", item.label) ~~"""
def gui_listbox_items_convert_headers (items):
    """Convert a flat string list into a listbox-ready list with collapsible headers.
    
    Items prefixed with ``>>`` become ``LayoutListBoxHeader`` objects; all
    others pass through as plain strings. Pass the result to ``gui_list_box``
    with ``collapsible=True`` to enable collapse on header click.
    
    Args:
        items (list[str]): Flat list of strings. Prefix a string with ``>>``
            to make it a collapsible header, e.g. ``">>Section A"``.
    
    Returns:
        list[str | LayoutListBoxHeader]: Mixed list ready for ``gui_list_box``.
    
    Example:
        items = gui_listbox_items_convert_headers(
            [">>Section A", "Item 1", "Item 2", ">>Section B", "Item 3"]
        )
        gui_list_box(items, style="", select=True, collapsible=True)"""
