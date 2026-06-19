from sbs_utils.helpers import FrameContext
from sbs_utils.pages.layout.hole import Hole
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
def gui_hole (count=1, style=None):
    """Reserve empty column space that the next layout item expands to fill.
    
    Unlike ``gui_blank``, a hole is consumed by the following item as extra
    width. Use it to make a single element span multiple column slots.
    
    Args:
        count (int, optional): Number of extra column slots to reserve.
            Defaults to 1.
        style (str, optional): CSS-like style overrides. Defaults to None.
    
    Returns:
        Hole: The last hole layout item created.
    
    Example:
        gui_hole(2)
        gui_text("This text spans 3 columns")"""
