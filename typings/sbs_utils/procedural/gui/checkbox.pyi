from sbs_utils.pages.layout.checkbox import Checkbox
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
def gui_checkbox (msg, style=None, var=None, data=None):
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
        gui_checkbox("Enable auto-fire", var="auto_fire_on")"""
