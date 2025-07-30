from sbs_utils.helpers import FrameContext
from sbs_utils.pages.layout.ship import Ship
def apply_control_styles (control_name, extra_style, layout_item, task):
    ...
def gui_ship (props, style=None):
    """renders a 3d image of the ship
    
    Args:
        props (str): The ship key
        style (str, optional): Style. Defaults to None.
    
    Returns:
        layout object: The Layout object created"""
