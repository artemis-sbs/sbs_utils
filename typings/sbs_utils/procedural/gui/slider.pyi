from sbs_utils.helpers import FrameContext
from sbs_utils.pages.layout.slider import Slider
def apply_control_styles (control_name, extra_style, layout_item, task):
    ...
def gui_int_slider (msg, style=None, var=None, data=None):
    """Draw an integer slider control
    
    Args:
        props (str): hi, low etc.
        style (style, optional): Style. Defaults to None.
        var (str, optional): Variable name to set the selection to. Defaults to None.
        data (object, optional): data to pass the handler. Defaults to None.
    
    Returns:
        layout object: The Layout object created"""
def gui_slider (msg, style=None, var=None, data=None, is_int=False):
    """Draw a slider control
    
    Args:
        props (str): hi, low etc.
        style (style, optional): Style. Defaults to None.
        var (str, optional): Variable name to set the selection to. Defaults to None.
        data (object, optional): data to pass the handler. Defaults to None.
        is_int (bool): Use only integers values
    
    Returns:
        layout object: The Layout object created"""
