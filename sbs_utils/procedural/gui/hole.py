from ...helpers import FrameContext
from ..style import apply_control_styles

from ...pages.layout.hole import Hole
def gui_hole(count=1, style=None):
    """Reserve empty column space that the next layout item expands to fill.

    Unlike ``gui_blank``, a hole is consumed by the following item as extra
    width. Use it to make a single element span multiple column slots.

    Args:
        count (int, optional): Number of extra column slots to reserve.
            Defaults to 1.
        style (str, optional): CSS-like style overrides. Defaults to None.

    Returns:
        Hole: The last hole layout item created.

    Example:
        gui_hole(2)
        gui_text("This text spans 3 columns")
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
