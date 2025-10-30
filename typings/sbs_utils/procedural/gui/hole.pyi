from sbs_utils.helpers import FrameContext
from sbs_utils.pages.layout.hole import Hole
def apply_control_styles (control_name, extra_style, layout_item, task):
    """Apply style information to a layout item based on the type of the layout, and apply the extra styles as needed.
    Args:
        control_name (str): The name of the control style.
        extra_style (str): A CSS-style string containing extra style definitions which override those in the control style.
        layout_item (LayoutItem): The layout item for which the style is to be applied."""
def gui_hole (count=1, style=None):
    """adds an empty column that is used by the next item
    
    Args:
        count (int): The number of columns to use
        style (_type_, optional): Style. Defaults to None.
    
    Returns:
        layout object: The Layout object created"""
