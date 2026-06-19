from sbs_utils.helpers import FrameContext
from sbs_utils.pages.layout.radio_button_group import RadioButtonGroup
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
def gui_radio (msg, style=None, var=None, data=None, vertical=False):
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
        gui_radio("Beam,Missile,Mine", var="weapon_type")"""
def gui_vradio (msg, style=None, var=None, data=None):
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
        gui_vradio("Alpha,Beta,Gamma", var="choice")"""
