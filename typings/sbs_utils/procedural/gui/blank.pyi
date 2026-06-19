from sbs_utils.pages.layout.blank import Blank
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
def gui_blank (count=1, style=None):
    """Add one or more empty columns to the current layout row.
    
    Blanks occupy column space without rendering anything visible. Use them
    to push elements right, add padding, or center icons.
    
    Args:
        count (int, optional): Number of blank columns to insert. Defaults to
            1.
        style (str, optional): CSS-like style overrides applied to each blank.
            Defaults to None.
    
    Returns:
        Blank: The last blank layout item created.
    
    Example:
        gui_blank()
        gui_icon("icons/shield")
        gui_blank()"""
