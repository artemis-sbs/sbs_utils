from ...helpers import FrameContext
from ..style import apply_control_styles
from ...pages.widgets.layout_listbox import LayoutListbox, LayoutListBoxHeader



def gui_listbox_items_convert_headers(items):
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
        (list(str|LayoutListBoxHeader)): A list of LayoutListBoxHeader (for the headers) and strings (for the items)
    """
    ret = []
    for k in items:
        if isinstance(k,str):
            collapse = False
            if k.startswith(">>"):
                k = k[2:]
                ret.append(LayoutListBoxHeader(k, collapse))
            else:
                ret.append(k)
    return ret

def gui_list_box_is_header(item):
    """Created a gui_list_box_header element

    Args:
        label (str): The label text
        collapse (bool, optional): Default the collapsed state. Defaults to False.

    Returns:
        _type_: _description_
    """
    return isinstance(item, LayoutListBoxHeader)


def gui_list_box_header(label, collapse=False, indent=0, selectable=False, data=None, visual_indent=None):
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
        LayoutListBoxHeader : _description_
    """
    return LayoutListBoxHeader(label, collapse, indent, selectable, data, visual_indent)

def gui_list_box(items, style, 
                 item_template=None, title_template=None, 
                 section_style=None, title_section_style=None,
                 select=False, multi=False, carousel=False,  collapsible=False,read_only=False):
    """
    Build a LayoutListBox gui element

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
        The LayoutListBox layout object
    """
    page = FrameContext.page
    task = FrameContext.task
    if page is None:
        return None
    tag = page.get_tag()
    # The gui_content sets the values
    layout_item = LayoutListbox(0, 0, tag, items,
                 item_template, title_template, 
                 section_style, title_section_style,
                 select,multi, carousel,  collapsible, read_only)
    # #layout_item.data = data
    # if var is not None:
    #     layout_item.var_name = var
    #     layout_item.var_scope_id = task.get_id()
    #     layout_item.update_variable()

    apply_control_styles(".listbox", style, layout_item, task)
    # Last in case tag changed in style
    page.add_content(layout_item, None)
    return layout_item


