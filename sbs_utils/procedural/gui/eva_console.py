"""The EVA crew console: the relic out the visor, and the device in your hand.

The sibling of `boarding_console.py`, and deliberately only one line different. Grid
boarding watches `ship_internal_view` - a deck seen from above, because a deck is what you
are on. A relic has no deck, so this watches `3dview`: the suit, in the ruin, from outside
it. Everything to the right of the map is the same xESS, drawn by the same code, in the
same two bands.

    == eva_console
        gui_eva_console()
        on change eva_console_revision():
            gui_eva_console_tick()
        await gui()

BUILD ONCE, THEN UPDATE, and the `on change` calls a FUNCTION rather than jumping back to
the label - for the reason written out in `boarding_console.py`: a repaint re-sends every
widget on the screen over the network, and a screen caught mid-build is what "it repaints
empty" gets reported as.

THE CONSOLE MUST BE ASSIGNED TO THE SUIT, not merely pointed at it. `3dview` draws
whatever the client is assigned to; re-aiming a camera without assigning gives a black
frame, which `camera.py` documents as the first thing everybody gets wrong. That is why
`gui_eva_console` assigns rather than leaving it to the caller - a console that forgets
looks like a broken view, not like a missing call.
"""
from ...helpers import FrameContext

# On the page, so it dies with the page rather than outliving it on a module.
VIEW = "__eva_console_view__"

#: How much of the screen the relic takes. The same default as the interior map, so a
#: crew member moving between the two body models sees the device stay where it was.
MAP_WIDTH_DEFAULT = 66

#: The camera this console rides. One of the engine's 3dview modes - `chase`,
#: `first_person`, `tracking` - or `cinematic`.
#:
#: NOT `cinematic`, and that is the point. The cinematic director picks its own shots and
#: keeps changing them, which is right for a cutscene and wrong for a cockpit: a pilot
#: whose viewpoint jumps every few seconds cannot tell which way the suit is pointing, and
#: the one thing this console exists to show is where you are going. Owner-reported on a
#: bridge, 2026-09-17: "the camera changing position is annoying."
#:
#: `chase` sits behind the suit and stays there - the standard main-screen flying view.
#:
#: **`third` IS THE DEFAULT NOW**, and it is `chase` with the three things `chase` cannot
#: have, because `set_main_view_modes` does not expose them: a distance, an orbit, and a
#: clamp that keeps the lens out of the rock. See `eva_camera.py` for why a relic needs
#: all three. `chase` is still here, and is still the right answer if a mission wants the
#: engine's own framing back.
CAMERA_MODE_DEFAULT = "third"

_camera_mode = CAMERA_MODE_DEFAULT


def eva_camera_mode(mode=None):
    """Read, or set, the camera every EVA console rides.

    Args:
        mode (str, optional): `third` (ours - see `eva_camera.py`), or one of the engine's
            own: `chase`, `first_person`, `tracking`, `cinematic`. Omit to read the
            current one.

    Returns:
        str: the mode in force.
    """
    global _camera_mode
    if mode is not None:
        _camera_mode = str(mode)
    return _camera_mode


def _ride_camera(client_id):
    """Point this console's main view at the suit it is assigned to.

    `cinematic` goes through `gui_cinematic_auto` because that mode needs its
    `cinematic_control` call as well as the view mode; everything else is the plain view
    mode, which is what keeps the camera still.
    """
    if _camera_mode == "third":
        # OURS, and the distinction that matters is not the view mode - it is who is
        # driving. `gui_cinematic_full_control` sends `scriptControlsCamera = 1`, which
        # takes the engine's director OUT of it; `gui_cinematic_auto` sends 0, which is
        # what hands the shot picking back and what "the camera changing position is
        # annoying" was actually about. `camera_track` sets the view mode itself, so
        # there is nothing to set here.
        from .eva_camera import eva_camera_aim, eva_camera_watch
        try:
            eva_camera_aim(client_id)
            # The console build aims once so there is no black frame before the first
            # tick; the pass takes it from there. Idempotent, so every console asking is
            # one watcher.
            eva_camera_watch()
        except Exception:                                # noqa: BLE001
            pass
        return _camera_mode
    if _camera_mode == "cinematic":
        from .cinematic import gui_cinematic_auto
        gui_cinematic_auto(client_id)
        return _camera_mode
    ctx = FrameContext.context
    sbs = getattr(ctx, "sbs", None) if ctx is not None else None
    if sbs is None:
        return _camera_mode
    try:
        sbs.set_main_view_modes(client_id, "3dview", "front", _camera_mode)
    except Exception:                                    # noqa: BLE001
        # A console on its way out, or an engine that does not know the mode. A view that
        # kept its last camera is a far better outcome than a console build that raised.
        pass
    return _camera_mode


def _client(client_id=None):
    if client_id is not None:
        return client_id
    page = FrameContext.page
    return getattr(page, "client_id", None) if page is not None else None


def eva_console_revision(client_id=None):
    """A value that changes when anything on this console's screen should change.

    Per CONSOLE, not global: one boarder arriving somewhere must not repaint the other
    five screens.

    THE SUIT'S DESTINATION IS IN HERE through the device's own revision - `xess_revision`
    folds in every app's badge, and NAV's badge carries the distance left to run. Without
    that the screen would freeze the moment a destination was picked and never show the
    suit arriving.
    """
    from ..boarding import boarding_me
    from ..eva import eva_my_suit, eva_where
    from .xess import xess_revision
    cid = _client(client_id)
    if cid is None:
        return 0
    return (boarding_me(cid), eva_my_suit(cid), eva_where(cid), xess_revision(cid))


def gui_eva_console(client_id=None, map_width=MAP_WIDTH_DEFAULT, suit=None):
    """Build the EVA console: the relic on the left, the xESS on the right.

    Args:
        client_id (optional): the console. Defaults to the page's own.
        map_width (int, optional): how much of the screen the view takes, in percent.
        suit (optional): the ship to ride. Defaults to the one this console was given by
            :func:`eva_take`.

    Returns:
        dict: the held widgets, also stored on the page for :func:`gui_eva_console_tick`.
    """
    from ..eva import eva_my_suit
    from .boarding_console import boarding_panel_width
    from .console import gui_activate_console
    from .section import gui_section
    from .widgets import gui_layout_widget
    from .xess import gui_xess

    cid = _client(client_id)
    # ONE call sets the width for the map AND for the device - they read the same two
    # area functions, and a console that sets only its own half draws a gap or an overlap.
    boarding_panel_width(map_width)

    # THE VIEW, IN ITS OWN SECTION. An engine widget draws at its own size over anything
    # MAST puts beside it, so it never shares a row: the controls do not overlap it, they
    # disappear under it.
    gui_section("area:0,0,%d,100;" % map_width)
    gui_activate_console("cinematic")
    gui_layout_widget("3dview")

    ride = suit if suit is not None else eva_my_suit(cid)
    if ride is not None:
        _assign(cid, ride)
        _ride_camera(cid)

    # THE DEVICE, unchanged. It opens its own section for the bar and its own region for
    # the apps, so the geometry lives in one place rather than being split across files.
    device = gui_xess(cid)

    view = {"cid": cid, "suit": ride, "device": device,
            "rev": eva_console_revision(cid)}
    page = FrameContext.page
    if page is not None:
        setattr(page, VIEW, view)
    return view


def _assign(client_id, ship):
    """Seat the console on the suit. Quiet when there is no engine to tell."""
    from ..query import to_id
    ctx = FrameContext.context
    sbs = getattr(ctx, "sbs", None) if ctx is not None else None
    if sbs is None:
        return False
    try:
        sbs.assign_client_to_ship(client_id, to_id(ship))
    except Exception:                                    # noqa: BLE001
        # A suit that has already gone, mid-teardown. Ordinary; the screen is on its way
        # out anyway, and raising here would take the whole console build with it.
        return False
    return True


def gui_eva_console_tick():
    """Refresh the EVA console in place. What an `on change` should CALL.

    Returns:
        bool: False when the screen is gone - a handler can outlive the page that
        registered it, and this is called from one.
    """
    from ..eva import eva_my_suit
    from .xess import gui_xess_tick
    page = FrameContext.page
    view = getattr(page, VIEW, None) if page is not None else None
    if not view:
        return False
    cid = view["cid"]
    view["rev"] = eva_console_revision(cid)

    # THE SUIT CAN BE REPLACED UNDER A LIVE SCREEN - a console taking over another
    # boarder's suit, or being handed one after the screen was already up. Re-seating here
    # costs a comparison and saves a black view that only a reroute would have cleared.
    ride = eva_my_suit(cid)
    if ride is not None and ride != view.get("suit"):
        view["suit"] = ride
        _assign(cid, ride)
        _ride_camera(cid)

    # The device owns every widget that changes. The view is an engine widget and looks
    # after itself.
    return gui_xess_tick()
