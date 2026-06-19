from sbs_utils.helpers import FrameContext
from sbs_utils.pages.layout.ship import Ship
def apply_control_styles (control_name, extra_style, layout_item, task):
    """Apply a named control style and optional overrides to a layout item.
    
    ``extra_style`` may be a raw CSS-style string (``"key:value;..."``) or
    a style name. It is applied on top of the base ``control_name`` style.
    
    Args:
        control_name (str): Base control style name.
        extra_style (str | dict | None): Additional style string, name, or
            parsed dict applied after the base style.
        layout_item (LayoutItem): Layout item to receive the style.
        task (MastAsyncTask): GUI task used for string formatting."""
def gui_ship (props, style=None):
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
        gui_ship("battleship", style="area:20,0,80,60;")"""
