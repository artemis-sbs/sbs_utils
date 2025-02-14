from ...helpers import FrameContext
from ..style import apply_control_styles

def gui_row(style=None):
    """queue a gui row

    Args:
        style (str, optional): Style. Defaults to None.

    Returns:
        layout object: The Layout object created
    """                
    page = FrameContext.page
    task = FrameContext.task
        
    if page is None:
        return None
    
    page.add_row()
    layout_item = page.get_pending_row()
    apply_control_styles(".row", style, layout_item, task)
    return layout_item

