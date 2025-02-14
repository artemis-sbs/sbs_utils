from ...helpers import FrameContext
from ..style import apply_control_styles

from ...pages.layout.hole import Hole
def gui_hole(count=1, style=None):
    """adds an empty column that is used by the next item

    Args:
        count (int): The number of columns to use
        style (_type_, optional): Style. Defaults to None.

    Returns:
        layout object: The Layout object created
    """        
    page = FrameContext.page
    task = FrameContext.task
    if page is None:
        return None
    layout_item = None
    for _ in range(count):
        # Log warning
        layout_item = Hole()
        apply_control_styles(".hole", style, layout_item, task)
        # Last in case tag changed in style
        page.add_content(layout_item, None)
    return layout_item
