from sbs_utils.helpers import FrameContext
from sbs_utils.pages.layout.hole import Hole
def apply_control_styles (control_name, extra_style, layout_item, task):
    ...
def gui_hole (count=1, style=None):
    """adds an empty column that is used by the next item
    
    Args:
        count (int): The number of columns to use
        style (_type_, optional): Style. Defaults to None.
    
    Returns:
        layout object: The Layout object created"""
