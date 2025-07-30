from sbs_utils.helpers import FrameContext
from sbs_utils.pages.layout.image import Image
def apply_control_styles (control_name, extra_style, layout_item, task):
    ...
def gui_image (props, style=None, fit=0):
    """queue a gui image element that draw based on the fit argument. Default is stretch
    
    Args:
        props (str): _description_
        style (str, optional): Style. Defaults to None.
        fit (int): The type of fill,
    
    Returns:
        layout object: The Layout object created"""
def gui_image_absolute (props, style=None):
    """queue a gui image element that draw the absolute pixels dimensions
    
    Args:
        props (str): _description_
        style (str, optional): Style. Defaults to None.
    
    Returns:
        layout object: The Layout object created"""
def gui_image_keep_aspect_ratio (props, style=None):
    """queue a gui image element that draw keeping the same aspect ratio, left top justified
    
    Args:
        props (str): _description_
        style (str, optional): Style. Defaults to None.
    
    Returns:
        layout object: The Layout object created"""
def gui_image_keep_aspect_ratio_center (props, style=None):
    """queue a gui image element that keeps the aspect ratio and centers when there is extra
    
    Args:
        props (str): _description_
        style (str, optional): Style. Defaults to None.
    
    Returns:
        layout object: The Layout object created"""
def gui_image_stretch (props, style=None):
    """queue a gui image element that stretches to fit
    
    Args:
        props (str): _description_
        style (str, optional): Style. Defaults to None.
    
    Returns:
        layout object: The Layout object created"""
