from ...helpers import FrameContext
from ..style import apply_control_styles
from ...pages.layout.checkbox import Checkbox
def gui_checkbox(msg, style=None, var=None, data=None):
    """Add a checkbox to the current GUI layout.

    The current value of ``var`` (expected to be a bool) sets the initial
    checked state. When the player toggles the checkbox, ``var`` is updated.

    Args:
        msg (str): Label text or property string shown next to the checkbox,
            e.g. ``"Enable shields"`` or ``"$text:Active;color:white;"``.
        style (str, optional): CSS-like style overrides. Defaults to None.
        var (str, optional): Variable name to read the initial checked state
            from and update on toggle. Defaults to None.
        data (object, optional): Arbitrary data passed to the event handler.
            Defaults to None.

    Returns:
        Checkbox: The layout item created.

    Example:
        gui_checkbox("Enable auto-fire", var="auto_fire_on")
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
