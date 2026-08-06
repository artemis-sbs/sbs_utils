from sbs_utils.helpers import FrameContext
from sbs_utils.pages.layout.slider import Slider
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
def gui_int_slider (msg, style=None, var=None, data=None):
    """Add an integer-only slider control to the current GUI layout.
    
    Convenience wrapper for ``gui_slider(..., is_int=True)``.
    
    Args:
        msg (str): Property string defining the slider range and label, e.g.
            ``"low:1;high:10;text:int;"``
        style (str, optional): CSS-like style overrides. Defaults to None.
        var (str, optional): Variable name to read the initial value from and
            update on change. Defaults to None.
        data (object, optional): Arbitrary data passed to the event handler.
            Defaults to None.
    
    Returns:
        Slider: The layout item created.
    
    Example:
        gui_int_slider("low:1;high:5;text:int;", var="torp_count")"""
def gui_slider (msg, style=None, var=None, data=None, is_int=False):
    """Add a slider control to the current GUI layout.
    
    The current value of ``var`` is used as the initial slider position. When
    the player adjusts the slider, ``var`` is updated.
    
    Args:
        msg (str): Property string defining the slider range and label, e.g.
            ``"low:0;high:100;text:float;"``
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
        gui_slider("low:0;high:100;text:float;", var="speed_pct")"""
