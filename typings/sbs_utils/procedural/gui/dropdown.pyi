from sbs_utils.pages.layout.dropdown import Dropdown
from sbs_utils.helpers import FrameContext
def apply_control_styles (control_name, extra_style, layout_item, task):
    ...
def gui_drop_down (props, style=None, var=None, data=None):
    """Draw a gui drop down list
    
    Args:
        props (str):
        style (style, optional): Style. Defaults to None.
        var (str, optional): Variable name to set the selection to. Defaults to None.
        data (object, optional): data to pass the handler. Defaults to None.
    
    Returns:
        layout object: The Layout object created"""
