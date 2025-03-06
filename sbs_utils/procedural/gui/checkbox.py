from ...helpers import FrameContext
from ..style import apply_control_styles
from ...pages.layout.checkbox import Checkbox
def gui_checkbox(msg, style=None, var=None, data=None):
    """ Draw a checkbox 

    Args:
        props (str): 
        style (style, optional): Style. Defaults to None.
        var (str, optional): Variable name to set the value to. Defaults to None.
        data (object, optional): data to pass the handler. Defaults to None.

    Returns:
        layout object: The Layout object created
    """    
    page = FrameContext.page
    task = FrameContext.task
    if page is None:
        return None
    tag = page.get_tag()
    msg = task.compile_and_format_string(msg)
    value = False
    if var is not None:
        value = task.get_variable(var, False)

    layout_item = Checkbox(tag, msg, value)
    layout_item.data = data
    if var is not None:
        layout_item.var_name = var
        layout_item.var_scope_id = task.get_id()
    #     layout_item.update_variable()

    apply_control_styles(".checkbox", style, layout_item, task)
    # Last in case tag changed in style
    page.add_content(layout_item, None)
    return layout_item
