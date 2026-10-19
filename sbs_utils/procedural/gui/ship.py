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


def gui_ship_portrait(ship, style=None, color=None):
    """A hull as its pre-rendered PORTRAIT - an image, not a 3D view.

    Much cheaper than ``gui_ship`` wherever there are many of them (a listbox row each,
    a roster, a fleet card). The portrait comes from a portrait set (see
    ``ship_portrait_load``; the base game's loads itself). A hull with no portrait falls
    back to ``gui_ship``, so it always draws.

    Args:
        ship (str | int | Agent): a ship-data key, or a ship whose hull to show.
        style (str, optional): CSS-like style overrides. Defaults to None.
        color (str, optional): tint for the portrait. Defaults to None (as painted).

    Returns:
        Image | Ship: The layout item created.

    Example:
        gui_ship_portrait("tsn_light_cruiser", style="area:0,0,10,10;")
    """
    from ..ship_portraits import ship_portrait_image, _hull_key
    from .image import gui_image
    task = FrameContext.task
    if isinstance(ship, str) and task is not None:
        ship = task.compile_and_format_string(ship)
    key = ship_portrait_image(ship)
    if key is not None:
        return gui_image(key, style=style, fit=3, color=color)
    hull = _hull_key(ship)
    return gui_ship(hull, style=style) if hull else None
