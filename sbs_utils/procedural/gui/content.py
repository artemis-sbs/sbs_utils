from ...helpers import FrameContext
from ..style import apply_control_styles

from ...pages.layout.gui_control import GuiControl
def gui_content(content, style=None, var=None):
    """Place a python code widget e.g. list box using the layout system

    Args:
        content (widget): A gui widget code in python
        style (str, optional): Style. Defaults to None.
        var (str, optional): The variable to set the widget's value to. Defaults to None.

    Returns:
        layout object: The layout object
    """    
    page = FrameContext.page
    task = FrameContext.task
    if page is None:
        return None

    tag = page.get_tag()
    # gui control ShipPicker(0,0,"mast", "Your Ship")
    layout_item = GuiControl(tag, content)
    if var is not None:
        layout_item.var_name = var
        layout_item.var_scope_id = task.get_id()
        v = task.get_variable(var)
        layout_item.value =v

    apply_control_styles(None, style, layout_item, task)
    # Last in case tag changed in style
    page.add_content(layout_item, None)
    return layout_item


