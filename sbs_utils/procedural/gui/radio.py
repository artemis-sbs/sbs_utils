from ...helpers import FrameContext
from ..style import apply_control_styles


from ...pages.layout.radio_button_group import RadioButtonGroup
def gui_radio(msg, style=None, var=None, data=None, vertical=False):
    """Add a radio button group to the current GUI layout.

    The current value of ``var`` sets the initially selected option. When the
    player selects a button, ``var`` is updated to the selected label.

    Args:
        msg (str): Comma-separated button labels or property string, e.g.
            ``"Alpha,Beta,Gamma"`` or ``"items:Slow,Fast;"``
        style (str, optional): CSS-like style overrides. Defaults to None.
        var (str, optional): Variable name to read the initial selection from
            and update on selection. Defaults to None.
        data (object, optional): Arbitrary data passed to the event handler.
            Defaults to None.
        vertical (bool, optional): Stack buttons vertically. Defaults to
            ``False`` (horizontal).

    Returns:
        RadioButtonGroup: The layout item created.

    Example:
        gui_radio("Beam,Missile,Mine", var="weapon_type")
    """    
    page = FrameContext.page
    task = FrameContext.task
    if page is None:
        return None
    tag = page.get_tag()
    msg = task.compile_and_format_string(msg)
    val = ""
    if var is not None:
        val = task.get_variable(var, "")

    layout_item = RadioButtonGroup(tag, msg, val, vertical)
    layout_item.data = data
    if var is not None:
        layout_item.var_name = var
        layout_item.var_scope_id = task.get_id()

    
    apply_control_styles(".radio", style, layout_item.group_layout, task)
    apply_control_styles(".radio", style, layout_item, task)
    layout_item.group_layout.tag = layout_item.tag+":group"
    # Last in case tag changed in style
    page.add_content(layout_item, None)

    return layout_item

def gui_vradio(msg, style=None, var=None, data=None):
    """Add a vertical radio button group to the current GUI layout.

    Convenience wrapper for ``gui_radio(..., vertical=True)``.

    Args:
        msg (str): Comma-separated button labels or property string.
        style (str, optional): CSS-like style overrides. Defaults to None.
        var (str, optional): Variable name to read the initial selection from
            and update on selection. Defaults to None.
        data (object, optional): Arbitrary data passed to the event handler.
            Defaults to None.

    Returns:
        RadioButtonGroup: The layout item created.

    Example:
        gui_vradio("Alpha,Beta,Gamma", var="choice")
    """        
    return gui_radio(msg, style, var, data, True)
