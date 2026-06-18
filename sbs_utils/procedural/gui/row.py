from ...helpers import FrameContext
from ..style import apply_control_styles

def gui_row(style=None):
    """Start a new layout row, pushing subsequent items to the next line.

    Call before adding items that should appear on a fresh row. Without
    explicit rows, items flow left-to-right across the current row.

    Args:
        style (str, optional): CSS-like style overrides for the row container.
            Defaults to None.

    Returns:
        Row: The row layout object.

    Example:
        gui_text("Name:")
        gui_row()
        gui_input("", var="ship_name")
    """                
    page = FrameContext.page
    task = FrameContext.task
        
    if page is None:
        return None
    
    page.add_row()
    layout_item = page.get_pending_row()
    apply_control_styles(".row", style, layout_item, task)
    return layout_item

