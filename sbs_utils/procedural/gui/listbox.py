from ...helpers import FrameContext
from ..style import apply_control_styles
from ...pages.widgets.layout_listbox import LayoutListbox


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


