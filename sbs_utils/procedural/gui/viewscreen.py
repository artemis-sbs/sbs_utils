"""The main screen, driven from another console - "on screen" (VIEWSCREEN_PLAN.md).

The captain says "on screen" and somebody has to make it happen. That somebody is
usually science, who already has the thing selected; this is the state layer that lets
them say it.

Two halves. The first decides *who is driving this ship's main screen and what they are
pointing it at*; the second (from "The shots" down) makes the engine agree with that.
The data column that reads out what science knows about the subject is phase 3 and is
not here yet.

THE STATE LIVES ON THE SHIP, not on a console and not in a module global. Cosmos
already keeps ``MAIN_SCREEN_VIEW`` / ``_FACING`` / ``_MODE`` in the player ship's
inventory (``handlerhooks`` writes them on ``main_screen_change``; the mainscreen
label reads them back). Putting the viewer's own keys in the same place buys three
things for free:

* **Scope.** Science on the Artemis cannot change what the Intrepid's screen shows.
* **Reset.** ``Agent.clear()`` takes it, so there is no new container for the restart
  ledger to police.
* **Arbitration.** Helm's engine ``main_screen_control`` widget writes
  ``MAIN_SCREEN_VIEW`` through the same door. Last writer wins, and helm reaching for
  the control is helm taking the screen back - see ``viewscreen_helm_override``.

The arbitration compares the whole ``(view, facing, mode)`` triple against what the
viewer asked for, rather than treating any ``main_screen_change`` as a takeover. A
console that reconnects can replay the state it is already in, and that must not read
as helm overriding anything; a genuine change of view OR of facing must.
"""
from ...helpers import FrameContext
from ...mast.mast import DEBUG
from ..inventory import get_inventory_value, set_inventory_value
from ..query import to_id, to_object
from ..signal import signal_emit
from .camera import camera_assign, camera_auto, camera_dolly, camera_move_stop, camera_orbit
from .overlay import (consoles_of, overlay_auto_dwell, overlay_clear, overlay_register,
                      overlay_show, overlay_slot_define)
from .viewscreen_pages import viewscreen_pages


# The shots a console can ask for. "off" is not a shot - it is handing the screen back.
MODES = ("off", "dolly", "orbit", "tactical")

# The engine main-screen VIEW each mode needs. Facing and mode (chase/first_person,
# long/short) are deliberately left alone: the viewer has an opinion about WHAT the
# screen shows, not about how the crew had it framed, and a 2D "mode" value the engine
# expects for tactical is not ours to invent.
_MODE_VIEW = {
    "dolly":    "3d_view",
    "orbit":    "3d_view",
    "tactical": "tactical",
}

# Inventory keys on the player ship.
KEY_MODE = "VIEWER_MODE"        # one of MODES
KEY_SUBJECT = "VIEWER_SUBJECT"  # id of what the shot is about, 0 for none
KEY_EXPECT = "VIEWER_EXPECT"    # (view, facing, mode) the viewer last asked the engine for
KEY_PRIOR = "VIEWER_PRIOR"      # (view, facing, mode) from before the viewer took over

# On the CONSOLE, not the ship - see viewscreen_home_ship.
KEY_HOME = "VIEWER_HOME_SHIP"   # the ship this console belongs to, while a shot has it
KEY_ALT = "VIEWER_ALT_PREV"     # last alt-ship handed to the engine, so we do not re-send

# The running shots: ship id -> {"task", "leg", "prom", "yaw", "cids"}. A module-level
# per-mission container, so it is cleared and audited by the reset ledger.
_VIEWERS = {}

# How the shots are framed and timed. The distances are multiples of the subject's own
# size, so a starbase and a fighter both fill the frame.
FRAME_NEAR = 6.0        # hull radii at the closest point of a push in
FRAME_FAR = 16.0        # hull radii at the widest
FRAME_MIN = 250.0       # never closer than this, whatever the engine says the hull is
DEFAULT_RADIUS = 90.0   # when the engine tells us nothing about the subject's size
DOLLY_SECONDS = 22.0    # one leg: in, then out
ORBIT_SECONDS = 48.0    # one full turn
ORBIT_PITCH = 12.0
DOLLY_YAW = -25.0

# The data column. The SAME rect in both modes: in tactical the radar is reflowed to
# leave this gutter free (LM), in a 3D shot the engine renders full-bleed and the column
# is drawn over it. One geometry to tune, and the crew's eye does not move when the mode
# changes. Layer 21000 is above the view and BELOW hero cards and cutscenes (26000+), so
# a story beat still takes the screen off the viewer.
COLUMN_SLOT = "viewer_data"
COLUMN_RECT = (72.0, 9.0, 99.0, 96.0)
COLUMN_LAYER = 21000
overlay_slot_define(COLUMN_SLOT, COLUMN_RECT, draw_layer=COLUMN_LAYER)


# What a console's drop-down says, and what each label means. Kept HERE rather than in
# the console so the two cannot drift: a console builds its list from
# viewscreen_shot_props() and hands the chosen label straight back to viewscreen_mode_for.
# ASCII only - these are engine-rendered strings.
SHOT_LABELS = (
    ("Off", "off"),
    ("On Screen - Dolly", "dolly"),
    ("On Screen - Orbit", "orbit"),
    ("Tactical 2D", "tactical"),
)


def viewscreen_shot_props(current=None):
    """The whole property string for a shot drop-down.

    The list key is ``list:``, NOT ``items:`` - a dropdown built with the wrong key has
    no options to render and the engine dies allocating for it (`MemoryError: bad
    allocation`), which does not look like a typo from the outside. ``text:`` is the
    label shown while it is closed, so pass what is currently running.
    """
    labels = ",".join(label for label, _mode in SHOT_LABELS)
    return f"text:{current or SHOT_LABELS[0][0]};list:{labels}"


def viewscreen_mode_for(label):
    """The mode a drop-down label means. Unknown labels read as ``off`` - a console
    showing something we do not recognize must not leave the screen commandeered."""
    for text, mode in SHOT_LABELS:
        if text == label:
            return mode
    return "off"


def viewscreen_label_for(mode):
    """The drop-down label for a mode, so a repaint re-selects what is running."""
    for text, m in SHOT_LABELS:
        if m == mode:
            return text
    return SHOT_LABELS[0][0]


def _main_screen_state(ship_id):
    """The engine main-screen triple currently recorded for a ship."""
    return (get_inventory_value(ship_id, "MAIN_SCREEN_VIEW", "3d_view"),
            get_inventory_value(ship_id, "MAIN_SCREEN_FACING", "front"),
            get_inventory_value(ship_id, "MAIN_SCREEN_MODE", "chase"))


def viewscreen_mode(ship):
    """The shot this ship's main screen is running, or ``"off"``."""
    return get_inventory_value(to_id(ship), KEY_MODE, "off")


def viewscreen_subject(ship):
    """The id the shot is about, or 0."""
    return get_inventory_value(to_id(ship), KEY_SUBJECT, 0)


def viewscreen_is_live(ship):
    """Whether a console is currently driving this ship's main screen."""
    return viewscreen_mode(ship) != "off"


def viewscreen_consoles(ship):
    """The main-screen consoles of one ship - the audience every shot addresses.

    Narrowed to the SHIP's own screens, which is what keeps one bridge's viewer out of
    another's. Returns an empty set when no main screen is connected, which is normal
    and not an error.
    """
    return consoles_of(to_id(ship), consoles="mainscreen")


def viewscreen_set(ship, mode, subject=None):
    """Point this ship's main screen at something.

    Args:
        ship (Agent | int): the player ship whose screen this is.
        mode (str): one of ``MODES``. ``"off"`` is the same as ``viewscreen_clear``.
        subject (Agent | int, optional): what the shot is about - normally the science
            selection. ``None`` means no subject.

    Returns:
        bool: True when the state changed.
    """
    ship_id = to_id(ship)
    if ship_id is None:
        return False
    if mode not in MODES:
        # Deliberately not an exception: this is reachable from a drop-down, and a
        # console typo should not end the GUI task mid-repaint.
        DEBUG(f"[viewscreen] unknown mode {mode!r}; expected one of {MODES}")
        return False
    if mode == "off":
        return viewscreen_clear(ship_id)

    subject_id = to_id(subject) or 0
    was_live = viewscreen_is_live(ship_id)
    if was_live and viewscreen_mode(ship_id) == mode and viewscreen_subject(ship_id) == subject_id:
        return False

    # Remember what the crew had BEFORE the viewer took over, once - a shot changing to
    # another shot must not overwrite it with the previous shot's own framing, or
    # standing down restores a state the crew never chose.
    if not was_live:
        set_inventory_value(ship_id, KEY_PRIOR, _main_screen_state(ship_id))

    view = _MODE_VIEW[mode]
    _view, facing, screen_mode = _main_screen_state(ship_id)
    set_inventory_value(ship_id, "MAIN_SCREEN_VIEW", view)
    set_inventory_value(ship_id, KEY_EXPECT, (view, facing, screen_mode))
    set_inventory_value(ship_id, KEY_MODE, mode)
    set_inventory_value(ship_id, KEY_SUBJECT, subject_id)
    viewscreen_apply(ship_id)
    _announce(ship_id, mode, subject_id)
    return True


def viewscreen_clear(ship):
    """Hand the screen back, restoring the view the crew had before the viewer took it.

    Returns:
        bool: True if a viewer was running.
    """
    return _stand_down(to_id(ship), restore=True)


def viewscreen_helm_override(ship, view, facing, mode):
    """Helm touched the main-screen control: the viewer stands down.

    Called from the ``main_screen_change`` handler with the triple the engine just
    reported. No restore - helm's choice IS the new state, and putting the viewer's
    idea of "before" back over the top would undo the very change being handled.

    A triple identical to what the viewer asked for is NOT a takeover: a console
    reconnecting replays the state it is already in.

    The triple is written here as well as by the caller. ``handlerhooks`` already
    records it (issue #595) and writing it twice is harmless - but a function whose
    postcondition depends on the caller having gone first is a trap for the next
    caller, so this one leaves the ship in the state it was told about either way.

    Returns:
        bool: True if a viewer was stood down.
    """
    ship_id = to_id(ship)
    # Logged unconditionally, and before the guards: "did the engine even fire one of
    # these, and carrying what" is the first question every time this misbehaves, and it
    # is unanswerable after the fact otherwise.
    DEBUG(f"[viewscreen] main_screen_change on {ship_id}: {(view, facing, mode)} "
          f"(viewer={viewscreen_mode(ship_id) if ship_id else '?'}, "
          f"expected={get_inventory_value(ship_id, KEY_EXPECT, None) if ship_id else '?'})")
    if ship_id is None or not viewscreen_is_live(ship_id):
        return False
    expect = get_inventory_value(ship_id, KEY_EXPECT, None)
    if expect is not None and tuple(expect) == (view, facing, mode):
        return False
    # Say why. A viewer that vanishes on its own is the hardest kind of bug to report -
    # "it was working and then it stopped" - and the answer is always in this comparison.
    DEBUG(f"[viewscreen] helm override on {ship_id}: asked for {expect}, "
          f"engine reported {(view, facing, mode)}; standing down")
    stood_down = _stand_down(ship_id, restore=False)
    set_inventory_value(ship_id, "MAIN_SCREEN_VIEW", view)
    set_inventory_value(ship_id, "MAIN_SCREEN_FACING", facing)
    set_inventory_value(ship_id, "MAIN_SCREEN_MODE", mode)
    return stood_down


def _stand_down(ship_id, restore):
    if ship_id is None or not viewscreen_is_live(ship_id):
        return False
    # The consoles first: this hands back the camera, the assignment and the 2D focus,
    # and the state written below is what tells the rest of the system it is over.
    _viewer_stop(ship_id, release=False)
    _release_consoles(ship_id)
    if restore:
        prior = get_inventory_value(ship_id, KEY_PRIOR, None)
        if prior is not None:
            view, facing, mode = prior
            set_inventory_value(ship_id, "MAIN_SCREEN_VIEW", view)
            set_inventory_value(ship_id, "MAIN_SCREEN_FACING", facing)
            set_inventory_value(ship_id, "MAIN_SCREEN_MODE", mode)
    set_inventory_value(ship_id, KEY_MODE, "off")
    set_inventory_value(ship_id, KEY_SUBJECT, 0)
    set_inventory_value(ship_id, KEY_EXPECT, None)
    set_inventory_value(ship_id, KEY_PRIOR, None)
    _announce(ship_id, "off", 0)
    return True


# --- The shots ---------------------------------------------------------------
# Phase 2. Everything above decides WHAT the screen should be showing; this makes the
# engine agree with it.
#
# THE ASSIGNMENT IS THE THING TO KNOW. `camera_track` assigns a console to the object
# the lens rides, because the engine only honors a camera change when the two match -
# so while a shot runs, a main screen is assigned to the SUBJECT, which may well be
# somebody else's ship. Two consequences, both handled here:
#
#   * ``sbs.get_ship_of_client`` on that console no longer returns its own ship. Use
#     ``viewscreen_home_ship``.
#   * View culling follows the assigned object - which for a viewer is what you want
#     (the thing being looked at has to be rendered), but it is not nothing.
#
# Standing down puts the assignment back.

def viewscreen_home_ship(client_id):
    """The ship a console BELONGS to, even while a shot has it assigned elsewhere.

    Anything that means "this console's own ship" must ask this rather than
    ``sbs.get_ship_of_client``, which during a shot answers with the subject.
    """
    home = get_inventory_value(client_id, KEY_HOME, None)
    if home:
        return home
    return FrameContext.context.sbs.get_ship_of_client(client_id)


def viewscreen_framing(subject):
    """``(near, far)`` lens distances for a subject.

    Scaled off the hull's own size, so a starbase and a fighter both fill the frame
    rather than one being a speck and the other clipping the lens. ``exclusion_radius``
    is the only size the engine actually exposes; when it says nothing, a default that
    frames a mid-sized ship is better than a guess that frames nothing.
    """
    radius = DEFAULT_RADIUS
    obj = to_object(subject)
    eo = obj.space_object() if obj is not None else None
    r = getattr(eo, "exclusion_radius", 0.0) or 0.0
    if r > 0:
        radius = float(r)
    near = max(FRAME_MIN, radius * FRAME_NEAR)
    far = max(near * 1.6, radius * FRAME_FAR)
    return near, far


def viewscreen_apply(ship):
    """Make the engine match the recorded state. Safe to call repeatedly.

    This is the one place that touches cameras, so a console that connects late, a
    repaint, or a fresh ``viewscreen_set`` all arrive at the same behavior by calling it.

    Returns:
        int: how many consoles the shot is running on.
    """
    ship_id = to_id(ship)
    if ship_id is None:
        return 0
    mode = viewscreen_mode(ship_id)
    cids = viewscreen_consoles(ship_id)
    if mode == "off" or not cids:
        _viewer_stop(ship_id)
        return 0

    subject = viewscreen_subject(ship_id)
    if to_object(subject) is None and mode != "tactical":
        # Nothing to look at. Standing down is the honest answer - the library will not
        # pick a different subject, which is a directing decision it cannot make.
        viewscreen_clear(ship_id)
        return 0

    if mode == "tactical":
        # A 2D shot is not a camera move: the widget list changes (the mainscreen label
        # re-runs on the signal) and the radar is pointed at the subject. Coming from a
        # 3D shot, the console has to get its own ship back first - a radar centered on
        # the enemy is not what "tactical" means.
        _viewer_stop(ship_id)
        _restore_home(cids)
        for cid in cids:
            _alt_ship(cid, subject)
    else:
        _remember_home(cids)
    _viewer_start(ship_id, mode, subject, cids)
    return len(cids)


def viewscreen_reset():
    """Drop every running shot WITHOUT touching the engine - for mission reset.

    The tick tasks are already gone by then (``TickDispatcher.clear()``), and the
    clients these records name belong to a sim that is being torn down, so re-assigning
    their cameras is at best pointless. This just stops the records outliving the
    mission that made them.
    """
    _VIEWERS.clear()


def _remember_home(cids):
    """Record each console's own ship before a shot takes the assignment away."""
    sbs = FrameContext.context.sbs
    for cid in cids:
        if not get_inventory_value(cid, KEY_HOME, None):
            set_inventory_value(cid, KEY_HOME, sbs.get_ship_of_client(cid))


def _restore_home(cids):
    """Give each console its own ship back."""
    for cid in cids:
        home = get_inventory_value(cid, KEY_HOME, None)
        if home:
            camera_assign(cid, home)
            set_inventory_value(cid, KEY_HOME, None)
        _alt_ship(cid, 0)


def _alt_ship(cid, focus_id):
    """Point a console's 2D view at another object, at most once per change.

    Same shape as ``comms_set_2dview_focus`` - including the "did we already send this"
    latch, because the engine call is not free - but without the ``2d_follow`` gate:
    that flag is a science/comms CHECKBOX, and a main screen has no checkbox. Science
    choosing the shot is the intent.
    """
    focus_id = focus_id or 0
    if get_inventory_value(cid, KEY_ALT, 0) == focus_id:
        return
    FrameContext.context.sbs.assign_client_to_alt_ship(cid, focus_id)
    set_inventory_value(cid, KEY_ALT, focus_id)


def _viewer_start(ship_id, mode, subject, cids):
    """Begin (or re-begin) the running viewer: the moving shot, and the data column.

    ONE record and ONE ticker for both, because they are one thing to the crew and
    because a tactical shot has a column but no camera - two bookkeepers would mean two
    chances to leave one of them running.
    """
    _viewer_stop(ship_id, release=False)
    from ...tickdispatcher import TickDispatcher
    record = {"ship": ship_id, "mode": mode, "subject": subject, "cids": list(cids),
              "leg": 0, "yaw": 0.0, "prom": None, "task": None,
              "page": 0, "shown": None, "page_at": 0.0, "dwell": 0.0}
    _VIEWERS[ship_id] = record
    if mode != "tactical":
        _next_leg(record)
    _column_update(record, force=True)
    # One check a second, not one a tick: this notices that a leg or a page has run out.
    # The camera move itself is driven at full rate by the camera's own driver.
    record["task"] = TickDispatcher.do_interval(lambda t: _advance(ship_id, t), 1)


def _viewer_stop(ship_id, release=True):
    """Stop the moving shot.

    ``release=False`` when one shot is REPLACING another: the new shot re-points the
    same consoles a moment later, and handing them back in between would clear the home
    ship it is about to need - which stranded a console on the subject when a dolly
    followed an orbit.
    """
    record = _VIEWERS.pop(ship_id, None)
    if record is None:
        return False
    task = record.get("task")
    if task is not None:
        task.stop()
    cids = record["cids"]
    overlay_clear(COLUMN_SLOT, to=cids)
    camera_move_stop(cids)
    if release:
        camera_auto(cids)
    return True


def _release_consoles(ship_id):
    """Hand every one of this ship's main screens back: engine director, own ship, no
    2D focus.

    Separate from ``_shots_stop`` because a TACTICAL shot keeps no camera record at all
    and still has something to undo - the alt-ship focus. Standing down has to be one
    call that covers both, or 2D shots leak their focus.
    """
    cids = viewscreen_consoles(ship_id)
    if cids:
        camera_move_stop(cids)
        camera_auto(cids)
    _restore_home(cids)


def _advance(ship_id, task):
    """Start the next leg once the current one has run out."""
    record = _VIEWERS.get(ship_id)
    if record is None or record.get("task") not in (None, task):
        task.stop()
        return
    if to_object(record["subject"]) is None:
        # The subject was destroyed mid-shot. The engine drops to its own default view
        # rather than freezing, so there is nothing to hold on to.
        viewscreen_clear(ship_id)
        return
    if record["mode"] != "tactical":
        prom = record.get("prom")
        if prom is None or prom.done():
            _next_leg(record)
    _column_update(record)


def _next_leg(record):
    """One leg of the loop: a push in or out, or one turn of the orbit.

    Legs rather than one endless move because both shots have a natural length, and a
    loop made of finite legs recovers by itself - if a leg is cut short (subject gone,
    another console stealing the camera) the next tick just starts the next one.
    """
    near, far = viewscreen_framing(record["subject"])
    cids = record["cids"]
    if record["mode"] == "orbit":
        yaw = record["yaw"]
        record["prom"] = camera_orbit(cids, record["subject"], far, from_yaw=yaw,
                                      to_yaw=yaw + 360.0, seconds=ORBIT_SECONDS,
                                      pitch=ORBIT_PITCH)
        # Carry the angle over so the next turn starts where this one ended - a loop
        # that restarted at 0 would whip back round on every lap.
        record["yaw"] = (yaw + 360.0) % 360.0
    else:
        # Ping-pong: in, then out. A push that cut back to wide each time would read as
        # a jump cut every 22 seconds.
        a, b = (far, near) if record["leg"] % 2 == 0 else (near, far)
        record["prom"] = camera_dolly(cids, record["subject"], a, b, yaw=DOLLY_YAW,
                                      pitch=ORBIT_PITCH, seconds=DOLLY_SECONDS)
    record["leg"] += 1


# --- The data column ---------------------------------------------------------
# What science knows about the thing on screen, in the gutter beside it, paging itself
# when there is more than one screenful. The pages themselves are pure functions living
# in viewscreen_pages.py; this is only the surface and the clock.

def _column_builder(client_id, content):
    """One page of the column: a heading-and-body text area, plus a position dot row."""
    from .row import gui_row
    from .text import gui_text, gui_text_area

    text = content.get("text") or ""
    count = int(content.get("count") or 1)
    index = int(content.get("index") or 0)

    gui_row("row-height: 100-1.4em; background: #0009;")
    gui_text_area(text, "padding: 8px;")
    if count > 1:
        # Dots, not "3 / 7". It is a viewscreen, not a form - the crew needs to know
        # more is coming, not to count it.
        dots = " ".join("*" if i == index else "-" for i in range(count))
        gui_row("row-height: 1.4em; background: #0009;")
        gui_text(f"$text:{dots};justify:center;color:#8cf;")


overlay_register(COLUMN_SLOT, _column_builder)


def _column_pages(record):
    return viewscreen_pages(record["subject"], record["ship"])


def _column_update(record, force=False):
    """Re-render the column, advancing the page when the current one has had its time.

    Called once a second. Two things happen here, and they are deliberately separate:

    * the page ADVANCES when its dwell has run out and there is more than one page;
    * the current page is re-shown whenever its TEXT has changed, which is what keeps a
      live value (range, shields) live on a single-page column that never advances.

    Nothing is sent when neither happened - the guard is the text itself, so an
    unchanged column costs one page render a second and no engine traffic.
    """
    pages = _column_pages(record)
    if not pages:
        if record["shown"] is not None:
            overlay_clear(COLUMN_SLOT, to=record["cids"])
            record["shown"] = None
        return False

    now = FrameContext.sim_seconds or 0.0
    index = record["page"]
    if index >= len(pages):
        index = 0
    if (not force and len(pages) > 1
            and (now - record["page_at"]) >= record["dwell"]):
        index = (index + 1) % len(pages)

    name, text = pages[index]
    if not force and index == record["page"] and text == record["shown"]:
        return False

    if index != record["page"] or force:
        record["page_at"] = now
        record["dwell"] = overlay_auto_dwell(text)
    record["page"] = index
    record["shown"] = text
    overlay_show(COLUMN_SLOT, COLUMN_SLOT, to=record["cids"],
                 text=text, index=index, count=len(pages), page=name)
    return True


def _announce(ship_id, mode, subject_id):
    """Tell the mainscreen consoles the state changed.

    One signal for every transition, including standing down, so the listener is a
    single route rather than one per verb. The work it triggers (camera, column) is
    server-side, so the route that does it is ``//shared/signal/viewscreen`` - five
    consoles must not start five orbits.
    """
    signal_emit("viewscreen", {"VIEWSCREEN_SHIP": ship_id,
                               "VIEWSCREEN_MODE": mode,
                               "VIEWSCREEN_SUBJECT": subject_id})
