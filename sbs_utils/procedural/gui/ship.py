from ...helpers import FrameContext
from ..style import apply_control_styles
from ...pages.layout.ship import Ship
def gui_ship(props, style=None):
    """Render a 3D ship model in the current GUI layout.

    Displays a real-time 3D render of the named ship type within the layout
    area. The ship type key must match one defined in the game data.

    Args:
        props (str): Ship type key or property string, e.g. ``"battleship"``
            or ``"$type:cruiser;angle:45;"``.
        style (str, optional): CSS-like style overrides. Defaults to None.

    Returns:
        Ship: The layout item created.

    Example:
        gui_ship("battleship", style="area:20,0,80,60;")
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
