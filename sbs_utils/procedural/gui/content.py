from ...helpers import FrameContext
from ..style import apply_control_styles

from ...pages.layout.gui_control import GuiControl
def gui_content(content, style=None, var=None):
    """Place a Python widget object into the layout system.

    Wraps a pre-built Python widget (e.g. a ship picker, custom control) in a
    ``GuiControl`` so it participates in the normal layout flow.

    Args:
        content (widget): A Python GUI widget object.
        style (str, optional): CSS-like style overrides. Defaults to None.
        var (str, optional): Variable name to bind the widget's value to.
            The current value of ``var`` is pushed into the widget and updates
            flow back when the widget changes. Defaults to None.

    Returns:
        GuiControl: The layout wrapper object.

    Example:
        picker = ShipPicker(0, 0, "mast", "Your Ship")
        gui_content(picker, var="selected_ship")
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


