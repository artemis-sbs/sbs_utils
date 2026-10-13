from sbs_utils.helpers import FrameContext
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
def gui_tilemap (follow=None, area=None, cols=17, style=None, on_click=None, fog=True, hints=None):
    """Add a tile map view to the current layout.
    
    Args:
        follow (optional): the actor the view keeps in sight - usually this console's
            own crew body. The view shows whichever area that actor is in.
        area (str, optional): a fixed area to show when nobody is followed.
        cols (int, optional): tiles across. Rows are however many square tiles fit.
        style (str, optional): layout style, as for any widget.
        on_click (callable, optional): ``fn(client_id, area, x, y)`` for a tile click.
        fog (bool, optional): draw only what the party has seen. On by default - a map
            must not show the crew what they do not know.
        hints (callable, optional): ``fn(client_id, area) -> {(x, y): atlas key}`` -
            badges drawn over cells worth a look (``boarding_hint_badges``). A badge
            may be ``(atlas key, tint)``.
    
    The area must EXIST before the page is built - load or generate it first. The
    engine only updates widgets that were in the build, so a view whose first paint
    found no area can draw nothing until the page is rebuilt (it logs once).
    
    Returns:
        TileView: the layout item.
    
    Example (MAST)::
    
        gui_section("area: 0, 0, 66, 100;")
        gui_tilemap(boarding_me(client_id), on_click=boarding_tile_click)"""
