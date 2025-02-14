from ...helpers import FrameContext
from ..style import apply_control_styles
from ...pages.layout.ship import Ship
def gui_ship(props, style=None):
    """renders a 3d image of the ship 

    Args:
        props (str): The ship key
        style (str, optional): Style. Defaults to None.

    Returns:
        layout object: The Layout object created
    """                
    page = FrameContext.page
    task = FrameContext.task
    props = task.compile_and_format_string(props)
    if page is None:
        return None
        
    
    # Log warning
    tag = page.get_tag()
    layout_item = Ship(tag,props)
    apply_control_styles(".ship", style, layout_item, task)
    # Last in case tag changed in style
    page.add_content(layout_item, None)
    return layout_item
