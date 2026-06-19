from sbs_utils.helpers import FrameContext
from sbs_utils.pages.layout.gui_control import GuiControl
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
def gui_content (content, style=None, var=None):
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
        gui_content(picker, var="selected_ship")"""
