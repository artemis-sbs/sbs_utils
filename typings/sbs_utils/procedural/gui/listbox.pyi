from sbs_utils.helpers import FrameContext
from sbs_utils.pages.widgets.layout_listbox import LayoutListBoxHeader
from sbs_utils.pages.widgets.layout_listbox import LayoutListbox
def apply_control_styles (control_name, extra_style, layout_item, task):
    """Apply style information to a layout item based on the type of the layout, and apply the extra styles as needed.
    Args:
        control_name (str): The name of the control style.
        extra_style (str): A CSS-style string containing extra style definitions which override those in the control style.
        layout_item (LayoutItem): The layout item for which the style is to be applied."""
def gui_list_box (items, style, item_template=None, title_template=None, section_style=None, title_section_style=None, select=False, multi=False, carousel=False, collapsible=False, read_only=False):
    """Build a LayoutListBox gui element
    
    Args:
        items: A list of the items that should be included
        style (str): Custom style attributes
        item_template (list(str|LayoutListBoxHeader)): A list of strings, or, if a header is desired, then that item should be a LayoutListBoxHeader object
        title_template (str|callable): if a callable, will call the function to build the title. If a string, then title_template will be used as the title of the listbox
        section_style (str): Style attributes for each section
        title_section_style (str): Style attributes for the title
        select (boolean): If true, item(s) within the listbox can be selected.
        multi (boolean): If true, multiple items can be selected. Ignored if `select` is None
        carousel (boolean): If true, will use the carousel styling, e.g. the ship type selection menu
        collapsible (boolean): If true, clicking on a header will collapse everything until the next header
        read_only (boolean): Can the items be modified
    Returns:
        The LayoutListBox layout object"""
def gui_list_box_header (label, collapse=False, indent=0, selectable=False, data=None, visual_indent=None):
    """Created a gui_list_box_header element
    
    Args:
        label (str): The label text
        collapse (bool, optional): Default the collapsed state. Defaults to False.
        indent (int): The indention level e.g. for a tree like structure
        selectable (bool): If the header is also selectable
        collapse_pixel_size (int): The size in pixels for the hit area (only used if selectable)
        select_first (bool): If the select area is before the collapse click area (only used if selectable)
        data (any): Optional additional data
    
    Returns:
        LayoutListBoxHeader : _description_"""
def gui_list_box_is_header (item):
    """Created a gui_list_box_header element
    
    Args:
        label (str): The label text
        collapse (bool, optional): Default the collapsed state. Defaults to False.
    
    Returns:
        _type_: _description_"""
def gui_listbox_items_convert_headers (items):
    """Converts a list of strings into a list of objects that allow a listbox to collapse if a header is clicked
    To make a header, prefix the name with `>>`.
    Example usage:
        ```python
        item = [">>Header","Item1","Item2",">>Another Header","Another Item 1","Another Item 2"]
        ret = gm_convert_listbox_items(item)
        gui_list_box(items=ret, style="", select=True, collapsible=True)
        ```
    Args:
        items (list(str)): A list of strings
    Returns:
        (list(str|LayoutListBoxHeader)): A list of LayoutListBoxHeader (for the headers) and strings (for the items)"""
