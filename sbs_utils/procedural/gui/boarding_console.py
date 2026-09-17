"""The crew console: the interior you are walking, and the device in your hand.

One call builds the whole screen, so a mission does not re-derive the layout. Without
this every boarding mission writes its own map-plus-panel by hand, and the first thing
each of them gets wrong is the same thing - an engine widget sharing a row with MAST
controls, which the engine draws over at its own size until the controls simply vanish.

    == crew_console
        gui_boarding_console()
        on change boarding_console_revision():
            gui_boarding_console_tick()
        await gui()

THE SHAPE IS BUILD-ONCE-THEN-UPDATE, and the `on change` calls a FUNCTION rather than
jumping back to the label. A repaint is not a local redraw: it re-sends every widget on
the screen over the network, to that console, on every change - and a screen caught
mid-build is what "it repaints empty" and "there are two lists" are reported as.

TWO BANDS, NOT THREE
--------------------
The map, and beside it the xESS: an identity bar and one app area. Everything the device
does is an app, including answering the scene and leaving the surface.

This replaces a three-band column whose bottom two were pinned regions and whose flow had
to reserve exactly their combined height with its last row. That arithmetic existed only
because three things were competing for the bottom of the column; with one region there
is nothing left to agree. `ACTIONS_BAND_PX`, `XESS_BODY_PX`, `boarding_reserve_px` and
`boarding_actions_area` are gone with it.

WHAT IS DELIBERATELY NOT HERE: `grid_object_list`, `grid_face` and `grid_control`. All
three follow the engine's grid SELECTION, which is one value per SHIP - several consoles
on one interior would each see their portrait and verb list follow whoever clicked last.
Giving them up is what lets a whole party board at once, and it is why the column on the
right exists at all.
"""
from ...helpers import FrameContext
from ..query import to_object

# On the page, so it dies with the page rather than outliving it on a module.
VIEW = "__boarding_console_view__"

ACCENT = "#8cf"
DIM = "#789"

#: The device column's right edge, in screen percent.
PANEL_RIGHT = 99

#: Where a console's content starts, in px. The ePADD's own `BODY_TOP_PX` - the engine's
#: strip is 35px on a 3% layout and LM has drawn from 45px since - so the two devices
#: begin on the same line rather than each guessing.
PANEL_TOP_PX = 45

#: The identity bar: who you are, and under it what you do and where you are standing.
#:
#: It is the only band on screen in EVERY state, the tile sheet included, which is why
#: the weapon's state lives there. An app you have navigated away from cannot warn you.
#:
#: TWO ROWS, BECAUSE A NAME IS LONGER THAN ONE SLOT. On one row the name shared its line
#: with the job and the room, so "Lieutenant Lt Mira Okonkwo" wrapped and the second line
#: fell out of the bar and over the app below it. The engine does not clip. Giving the
#: name a row of its own is the fix that does not depend on how long a name is: a crew
#: name comes from a roster, an auto-namer and a mission, and none of them agreed to
#: keep it short.
NAME_PX = 30
SUB_PX = 26
IDENTITY_PX = NAME_PX + SUB_PX

#: Where the app area begins. Stated as the bar's bottom rather than as a second number,
#: so the two cannot drift: both bands are px from the same origin, whatever the screen.
APP_TOP_PX = PANEL_TOP_PX + IDENTITY_PX

#: How much of the screen the interior takes, in percent. The device is everything right
#: of it. A default rather than a constant so a mission can hand a different width to
#: `gui_boarding_console`, but the bar and the region have to agree, so the last width
#: used is remembered here for them to read.
MAP_WIDTH_DEFAULT = 66
_map_width = MAP_WIDTH_DEFAULT


def panel_left():
    """The device column's left edge, matching whatever map width was last built."""
    return _map_width + 1


def boarding_identity_area():
    """The identity bar's absolute area."""
    return ("area: %d, %dpx, %d, %dpx;"
            % (panel_left(), PANEL_TOP_PX, PANEL_RIGHT, APP_TOP_PX))


def boarding_app_area():
    """The app area's absolute area - the bar's bottom edge, down to the screen's.

    Paired with :func:`boarding_identity_area` by construction: they share `APP_TOP_PX`,
    so they are adjacent and cannot overlap however the screen is sized. The old pair of
    regions needed a reserve row to keep the flow out of them; this one has no flow under
    it to keep out.
    """
    return ("area: %d, %dpx, %d, 100;" % (panel_left(), APP_TOP_PX, PANEL_RIGHT))


def _client(client_id=None):
    if client_id is not None:
        return client_id
    page = FrameContext.page
    return getattr(page, "client_id", None) if page is not None else None


def boarding_console_revision(client_id=None):
    """A value that changes when anything on this console's screen should change.

    What an `on change` watches. Per CONSOLE, not global: one crew member answering a
    choice must not repaint the other five screens, and a shared counter would.

    THE DEVICE IS PART OF THIS SCREEN. Without its revision here, opening an app changed
    the stored state and nothing ever repainted - the `on change` never moved, so the
    tick never ran and the tiles "did nothing".
    """
    from ..boarding import boarding_me
    from ..boarding_site import boarding_where
    from .xess import xess_revision
    cid = _client(client_id)
    if cid is None:
        return 0
    return (boarding_me(cid), boarding_where(cid), xess_revision(cid))


def where_text(client_id):
    """The room this console's character is standing in, in words.

    Public because the device's identity bar shows it and the two must not each work it
    out - a bar that disagrees with the map about which room you are in is worse than one
    that says nothing.
    """
    from ..boarding_site import (boarding_my_host, boarding_where, boarding_room_at,
                                 boarding_room_name, boarding_room_roles)
    at = boarding_where(client_id)
    if at is None:
        return "aboard"
    host = boarding_my_host(client_id)
    room = boarding_room_at(host, at[0], at[1], boarding_room_roles())
    if room is None:
        return "a corridor"
    return boarding_room_name(room.name)


def gui_boarding_console(client_id=None, map_width=66, on_leave=None):
    """Build the crew console: the interior on the left, the xESS on the right.

    Args:
        client_id (optional): the console. Defaults to the page's own.
        map_width (int, optional): how much of the screen the interior takes, in percent.
        on_leave (optional): ignored, and kept so a mission that passed it still runs.
            Leaving is the CREW app's Beam up now, which calls `boarding_go_up` - there
            is no longer a button on every screen to hand a handler to.

    Returns:
        dict: the held widgets, also stored on the page for
        :func:`gui_boarding_console_tick`.
    """
    from .section import gui_section
    from .widgets import gui_layout_widget
    from .xess import gui_xess

    cid = _client(client_id)
    global _map_width
    _map_width = map_width

    # THE MAP, IN ITS OWN SECTION. An engine widget draws at its own size over anything
    # MAST puts beside it, so it never shares a row - the controls do not overlap it,
    # they disappear under it.
    gui_section("area:0,0,%d,100;" % map_width)
    gui_layout_widget("ship_internal_view")

    # THE DEVICE. It opens its own section for the bar and its own region for the apps,
    # so the geometry lives in one place rather than being split across two files.
    device = gui_xess(cid)

    view = {"cid": cid, "device": device, "rev": boarding_console_revision(cid)}
    page = FrameContext.page
    if page is not None:
        setattr(page, VIEW, view)
    return view


def gui_boarding_console_tick():
    """Refresh the crew console in place. What an `on change` should CALL.

    Never `jump` back to the screen label instead: that re-sends every widget on the
    screen over the network to that console, and does it again on the next change,
    forever.

    Returns:
        bool: False when the screen is gone - a handler can outlive the page that
        registered it, and this is called from one.
    """
    from .xess import gui_xess_tick
    page = FrameContext.page
    view = getattr(page, VIEW, None) if page is not None else None
    if not view:
        return False
    view["rev"] = boarding_console_revision(view["cid"])
    # The device owns every widget that changes. The map is an engine widget and looks
    # after itself.
    return gui_xess_tick()
