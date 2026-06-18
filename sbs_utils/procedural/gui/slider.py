from ...helpers import FrameContext
from ..style import apply_control_styles
from ...pages.layout.slider import Slider
def gui_slider(msg, style=None, var=None, data=None, is_int=False):
    """Add a slider control to the current GUI layout.

    The current value of ``var`` is used as the initial slider position. When
    the player adjusts the slider, ``var`` is updated.

    Args:
        msg (str): Property string defining the slider range and label, e.g.
            ``"min:0;max:100;label:Energy;"``
        style (str, optional): CSS-like style overrides. Defaults to None.
        var (str, optional): Variable name to read the initial value from and
            update on change. Defaults to None.
        data (object, optional): Arbitrary data passed to the event handler.
            Defaults to None.
        is_int (bool, optional): Restrict values to integers. Defaults to
            ``False``.

    Returns:
        Slider: The layout item created.

    Example:
        gui_slider("min:0;max:100;label:Speed;", var="speed_pct")
    """    
    page = FrameContext.page
    task = FrameContext.page.gui_task
    
    if page is None:
        return None
    tag = page.get_tag()
    msg = task.compile_and_format_string(msg)
    val = 0
    if var is not None:
        val = task.get_variable(var, 0)

    layout_item = Slider(tag, val, msg, is_int)
    layout_item.data = data
    if var is not None:
        layout_item.var_name = var
        layout_item.var_scope_id = task.get_id()

    if is_int:
        apply_control_styles(".intslider", style, layout_item, task)
    else:
        apply_control_styles(".slider", style, layout_item, task)
    # Last in case tag changed in style
    page.add_content(layout_item, None)
    return layout_item

def gui_int_slider(msg, style=None, var=None, data=None):
    """Add an integer-only slider control to the current GUI layout.

    Convenience wrapper for ``gui_slider(..., is_int=True)``.

    Args:
        msg (str): Property string defining the slider range and label, e.g.
            ``"min:1;max:10;label:Count;"``
        style (str, optional): CSS-like style overrides. Defaults to None.
        var (str, optional): Variable name to read the initial value from and
            update on change. Defaults to None.
        data (object, optional): Arbitrary data passed to the event handler.
            Defaults to None.

    Returns:
        Slider: The layout item created.

    Example:
        gui_int_slider("min:1;max:5;label:Torpedo Count;", var="torp_count")
    """    
    return gui_slider(msg, style, var,  data, True)
