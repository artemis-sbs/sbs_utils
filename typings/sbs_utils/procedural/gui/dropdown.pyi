from sbs_utils.pages.layout.dropdown import Dropdown
from sbs_utils.helpers import FrameContext
def apply_control_styles (control_name, extra_style, layout_item, task):
    """Apply a named control style and optional overrides to a layout item.
    
    ``extra_style`` may be a raw CSS-style string (``"key:value;..."``) or
    a style name. It is applied on top of the base ``control_name`` style.
    
    Args:
        control_name (str): Base control style name.
        extra_style (str | dict | None): Additional style string, name, or
            parsed dict applied after the base style.
        layout_item (LayoutItem): Layout item to receive the style.
        task (MastAsyncTask): GUI task used for string formatting."""
def gui_drop_down (props, style=None, var=None, data=None):
    """Add a drop-down list to the current GUI layout.
    
    The current value of ``var`` sets the initially selected option. When the
    player selects an item, ``var`` is updated.
    
    Args:
        props (str): Semicolon-separated option list and optional properties,
            e.g. ``"items:Red,Green,Blue;"`` or ``"$items:Red,Green;color:white;"``.
        style (str, optional): CSS-like style overrides. Defaults to None.
        var (str, optional): Variable name to read the initial selection from
            and update on change. Defaults to None.
        data (object, optional): Arbitrary data passed to the event handler.
            Defaults to None.
    
    Returns:
        Dropdown: The layout item created.
    
    Example:
        gui_drop_down("items:Slow,Medium,Fast;", var="speed_setting")"""
