"""`gui_tilemap` - put a console's window onto a tile area on the page.

See ``pages/layout/tilemap_view.py`` for how it draws, and ``procedural/tilemap.py`` for
the world it draws.
"""
from ...helpers import FrameContext
from ..style import apply_control_styles


def gui_tilemap(follow=None, area=None, cols=17, style=None, on_click=None, fog=True,
                hints=None):
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
            badges drawn over cells worth a look (``boarding_hint_badges``).

    Returns:
        TileView: the layout item.

    Example (MAST)::

        gui_section("area: 0, 0, 66, 100;")
        gui_tilemap(boarding_me(client_id), on_click=boarding_tile_click)
    """
    from ...pages.layout.tilemap_view import TileView
    page = FrameContext.page
    task = FrameContext.task
    if page is None:
        return None
    view = TileView(page.get_tag(), follow=follow, area=area, cols=cols,
                    on_click=on_click, fog=fog, hints=hints)
    apply_control_styles(".tilemap", style, view, task)
    page.add_content(view, None)
    return view
