from ...helpers import FrameContext
from ..style import apply_control_styles
from ...pages.widgets.layout_listbox import LayoutListbox


def gui_list_box(items, style, 
                 item_template=None, title_template=None, 
                 section_style=None, title_section_style=None,
                 select=False, multi=False, carousel=False, read_only=False):
    
    page = FrameContext.page
    task = FrameContext.task
    if page is None:
        return None
    tag = page.get_tag()
    # The gui_content sets the values
    layout_item = LayoutListbox(0, 0, tag, items,
                 item_template, title_template, 
                 section_style, title_section_style,
                 select,multi, carousel, read_only)
    # #layout_item.data = data
    # if var is not None:
    #     layout_item.var_name = var
    #     layout_item.var_scope_id = task.get_id()
    #     layout_item.update_variable()

    apply_control_styles(".listbox", style, layout_item, task)
    # Last in case tag changed in style
    page.add_content(layout_item, None)
    return layout_item


