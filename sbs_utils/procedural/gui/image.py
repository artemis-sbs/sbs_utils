from ...helpers import FrameContext
from ..style import apply_control_styles

def gui_image_stretch(props, style=None):
    """queue a gui image element that stretches to fit

    Args:
        props (str): _description_
        style (str, optional): Style. Defaults to None.

    Returns:
        layout object: The Layout object created
    """            
    return gui_image(props, style=style, fit=0)

def gui_image_absolute(props, style=None):
    """queue a gui image element that draw the absolute pixels dimensions

    Args:
        props (str): _description_
        style (str, optional): Style. Defaults to None.

    Returns:
        layout object: The Layout object created
    """                
    return gui_image(props, style=style, fit=1)

def gui_image_keep_aspect_ratio(props, style=None):
    """queue a gui image element that draw keeping the same aspect ratio, left top justified

    Args:
        props (str): _description_
        style (str, optional): Style. Defaults to None.

    Returns:
        layout object: The Layout object created
    """                
    return gui_image(props, style=style, fit=2)

def gui_image_keep_aspect_ratio_center(props, style=None):
    """queue a gui image element that keeps the aspect ratio and centers when there is extra

    Args:
        props (str): _description_
        style (str, optional): Style. Defaults to None.

    Returns:
        layout object: The Layout object created
    """                
    return gui_image(props, style=style, fit=3)

from ...pages.layout.image import Image
def gui_image(props, style=None, fit=0):
    """queue a gui image element that draw based on the fit argument. Default is stretch

    Args:
        props (str): _description_
        style (str, optional): Style. Defaults to None.
        fit (int): The type of fill, 

    Returns:
        layout object: The Layout object created
    """                    
    page = FrameContext.page
    task = FrameContext.task
    props = task.compile_and_format_string(props)
    if page is None:
        return None
    
    if "image:" not in props:
        props = f"image:{props};"

    if "color:" not in props:
        props+="color:white;"
    
    tag = page.get_tag()
    layout_item = Image(tag,props, fit)
    apply_control_styles(".image", style, layout_item, task)
    # Last in case tag changed in style
    page.add_content(layout_item, None)
    return layout_item
