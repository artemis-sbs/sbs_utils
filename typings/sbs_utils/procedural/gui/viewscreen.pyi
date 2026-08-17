from sbs_utils.helpers import FrameContext
def DEBUG (msg):
    ...
def _advance (ship_id, task):
    """Start the next leg once the current one has run out."""
def _alt_ship (cid, focus_id):
    """Point a console's 2D view at another object, at most once per change.
    
    Same shape as ``comms_set_2dview_focus`` - including the "did we already send this"
    latch, because the engine call is not free - but without the ``2d_follow`` gate:
    that flag is a science/comms CHECKBOX, and a main screen has no checkbox. Science
    choosing the shot is the intent."""
def _announce (ship_id, mode, subject_id):
    """Tell the mainscreen consoles the state changed.
    
    One signal for every transition, including standing down, so the listener is a
    single route rather than one per verb. The work it triggers (camera, column) is
    server-side, so the route that does it is ``//shared/signal/viewscreen`` - five
    consoles must not start five orbits."""
def _column_builder (client_id, content):
    """One page of the column: a heading-and-body text area, plus a position dot row."""
def _column_pages (record):
    ...
def _column_update (record, force=False):
    """Re-render the column, advancing the page when the current one has had its time.
    
    Called once a second. Two things happen here, and they are deliberately separate:
    
    * the page ADVANCES when its dwell has run out and there is more than one page;
    * the current page is re-shown whenever its TEXT has changed, which is what keeps a
      live value (range, shields) live on a single-page column that never advances.
    
    Nothing is sent when neither happened - the guard is the text itself, so an
    unchanged column costs one page render a second and no engine traffic."""
def _main_screen_state (ship_id):
    """The engine main-screen triple currently recorded for a ship."""
def _next_leg (record):
    """One leg of the loop: a push in or out, or one turn of the orbit.
    
    Legs rather than one endless move because both shots have a natural length, and a
    loop made of finite legs recovers by itself - if a leg is cut short (subject gone,
    another console stealing the camera) the next tick just starts the next one."""
def _release_consoles (ship_id):
    """Hand every one of this ship's main screens back: engine director, own ship, no
    2D focus.
    
    Separate from ``_shots_stop`` because a TACTICAL shot keeps no camera record at all
    and still has something to undo - the alt-ship focus. Standing down has to be one
    call that covers both, or 2D shots leak their focus."""
def _remember_home (cids):
    """Record each console's own ship before a shot takes the assignment away."""
def _restore_home (cids):
    """Give each console its own ship back."""
def _stand_down (ship_id, restore):
    ...
def _viewer_start (ship_id, mode, subject, cids):
    """Begin (or re-begin) the running viewer: the moving shot, and the data column.
    
    ONE record and ONE ticker for both, because they are one thing to the crew and
    because a tactical shot has a column but no camera - two bookkeepers would mean two
    chances to leave one of them running."""
def _viewer_stop (ship_id, release=True):
    """Stop the moving shot.
    
    ``release=False`` when one shot is REPLACING another: the new shot re-points the
    same consoles a moment later, and handing them back in between would clear the home
    ship it is about to need - which stranded a console on the subject when a dolly
    followed an orbit."""
def camera_assign (to, obj, consoles=None):
    """Assign consoles to a space object - their identity, not their lens.
    
    The engine needs this before a cinematic camera means anything. It is normally called ONCE
    per console (typically onto a `camera_anchor`), and then the lens is moved freely with
    `camera_track`. Re-assigning per shot changes what the console *is* - which also changes
    what it can see, since view culling follows the assigned object, not the camera.
    
    Args:
        to: audience - a client id, a ship, a side, or a set/role query (see ``consoles_of``).
        obj: the space object (id or object) to assign them to.
        consoles (str, optional): narrow to consoles carrying these roles.
    
    Returns:
        int: how many consoles were assigned."""
def camera_auto (to=None, consoles=None):
    """Hand the camera back to the engine's own director (it follows the assigned ship).
    
    The release path for anything `camera_track` took over - end a cutscene with this.
    
    Args:
        to: audience (see ``consoles_of``); ``None`` is the current console.
        consoles (str, optional): narrow to consoles carrying these roles.
    
    Returns:
        int: how many consoles were released."""
def camera_dolly (to, subject, from_distance, to_distance, yaw=0.0, pitch=12.0, seconds=20.0, ease='in_out', consoles=None):
    """Push the lens in (or pull it out) along a fixed angle, FOLLOWING the subject.
    
    `camera_move` interpolates between two fixed WORLD points, which is right for a
    station and wrong for a ship under way: the shot is left behind, and what began as a
    push-in ends as a fly-past. This holds the ANGLE and changes only the distance,
    recomputing from wherever the subject is each tick - the same trick `camera_orbit`
    uses, and for the same reason.
    
    Args:
        from_distance / to_distance (float): radius at the start and the end. Give a
            larger ``from`` for a push in, a larger ``to`` for a pull out.
        yaw (float): degrees around the subject to sit at.
        pitch (float): degrees above it. Slightly down reads better than dead level.
    
    Returns:
        Promise: resolves when the push ends."""
def camera_move_stop (to=None, consoles=None):
    """Stop any running move on these consoles, leaving the lens where it is.
    
    Called for you by every move below: two drivers re-aiming the same console
    would fight tick by tick, and the symptom (a camera that jitters between two
    paths) reads as an engine bug rather than a second caller."""
def camera_orbit (to, subject, distance, from_yaw=0.0, to_yaw=360.0, seconds=10.0, pitch=15.0, ease='linear', consoles=None):
    """Swing the lens around `subject` at a fixed distance.
    
    Because offsets are world-space, this is the Game Master's move: recompute
    ``camera_orbit_lens`` each tick and re-aim. It follows a moving subject for free,
    since the offset is applied to wherever the subject is at the time.
    
    Args:
        distance (float): radius of the orbit.
        from_yaw / to_yaw (float): degrees to sweep between. Give ``to_yaw`` less
            than ``from_yaw`` to swing the other way.
        pitch (float): degrees above the subject. Default 15 looks down slightly,
            which reads better than dead level.
        ease (str): ``linear`` by default - an orbit that eases looks like a mistake.
    
    Returns:
        Promise: resolves when the sweep ends."""
def consoles_of (to, consoles=None):
    """Resolve an audience expression to a set of console client ids.
    
    Args:
        to: ``None`` (the current console), a client id, a ship id/object, a side
            key or side agent, or a set/list mixing any of those.
        consoles (str, optional): narrow to consoles with these roles, e.g.
            ``"mainscreen"`` or ``"science, comms"``.
    
    Returns:
        set[int]: console client ids (possibly empty)."""
def get_inventory_value (id_or_object, key: str, default=None):
    """Get an inventory value from an agent by key.
    
    Args:
        id_or_object (Agent | int): The agent ID or object.
        key (str): The inventory key.
        default (any, optional): Value returned when the key is absent.
            Defaults to None.
    
    Returns:
        any: The inventory value, or ``default`` if the key is not set."""
def is_alt_ship_target (id):
    """Return whether an ID is safe to hand to ``assign_client_to_alt_ship``.
    
    ``0`` means "clear the focus" and is always allowed. Anything else must be a
    SPACE-object id. A Fleet, side, task or grid id is script-only - the engine never
    created it - and pointing a console at one crashes the client: measured 5 runs out of
    5 as either a modal ``vertexIndex < numVerts`` assert out of ``DX11PAXVertList.cpp``
    or an access violation reading off the end of a vertex list. The engine takes the id
    as a ship, indexes a mesh it does not have, and reads whatever is there.
    
    A dead-but-well-formed space id is deliberately still allowed: the engine handles a
    deleted ship cleanly (measured), and rejecting it here would drop legitimate focus
    changes on a target that is merely mid-teardown. This guards the class the engine
    cannot survive, not staleness. ``object_exists`` already applies the same reasoning
    before calling ``space_object_exists``.
    
    Args:
        id (Agent | int): Agent ID or object.
    
    Returns:
        bool: ``True`` if the id is 0 or a space-object id."""
def overlay_auto_dwell (text):
    """Seconds to hold a piece of text: long enough to read, short enough to move on.
    
    Public because the viewscreen's data column paces its pages the same way, and one
    reading pace across every timed surface is the point."""
def overlay_clear (slot=None, to=None, consoles=None):
    """Clear one slot (or all slots if ``slot`` is None) on the ``to`` targets."""
def overlay_register (kind, builder):
    """Register a content builder for an overlay ``kind``.
    
    Args:
        kind (str): the ``kind`` value callers pass to ``overlay_show``.
        builder (callable): ``builder(client_id, content)`` — content is the dict
            passed to ``overlay_show`` (with ``kind`` included). Build widgets with
            the normal ``gui_*`` functions."""
def overlay_show (slot, kind, to=None, consoles=None, **content):
    """Show an overlay in ``slot`` using content builder ``kind``.
    
    Args:
        slot (str): a slot name (see ``OVERLAY_SLOTS``); unknown names use a
            centered default rect.
        kind (str): a registered builder (see ``overlay_register``).
        to: the audience — ``None`` = the current console; a client id; a **ship**
            (its consoles); a **side** key/agent (that side's consoles); or a set /
            role query mixing them. See ``consoles_of``.
        consoles (str, optional): narrow the audience to consoles with these roles,
            e.g. ``"mainscreen"``.
        **content: fields passed through to the builder.
    
    A console that joins the audience while this is still up gets it too — see
    the late-joiner note above. ``to=None`` means "the console calling", which has
    no audience to join, so it is not tracked."""
def overlay_slot_define (slot, rect, draw_layer=28000, input='passthrough'):
    """Define or override a slot's default rect / draw_layer / input mode."""
def set_inventory_value (so, key: str, value):
    """Set an inventory value on one or more agents.
    
    If ``so`` is a set or collection, every member receives the value.
    
    Args:
        so (Agent | int | set[Agent | int]): The agent(s) to update.
        key (str): The inventory key.
        value (any): The value to store."""
def signal_emit (name, data=None):
    """Emit a named signal, running all registered ``//signal/<name>`` routes.
    
    Safe to call when no MAST context is active — returns immediately with no
    side effects.
    
    Args:
        name (str): The signal name.
        data (dict, optional): Arbitrary data passed to each signal handler.
            Defaults to None."""
def to_id (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """Extract the integer ID from an agent, ``CloseData``, ``SpawnData``, or bare int.
    
    Args:
        other (Agent | CloseData | SpawnData | int): Value to convert.
    
    Returns:
        int: The integer agent ID."""
def to_object (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """Resolve an ID, ``CloseData``, or ``SpawnData`` to its Agent object.
    
    Returns ``None`` when the agent no longer exists.
    
    Args:
        other (Agent | CloseData | SpawnData | int): Value to resolve.
    
    Returns:
        Agent | None: The agent, or ``None`` if it could not be resolved."""
def viewscreen_apply (ship):
    """Make the engine match the recorded state. Safe to call repeatedly.
    
    This is the one place that touches cameras, so a console that connects late, a
    repaint, or a fresh ``viewscreen_set`` all arrive at the same behavior by calling it.
    
    Returns:
        int: how many consoles the shot is running on."""
def viewscreen_clear (ship):
    """Hand the screen back, restoring the view the crew had before the viewer took it.
    
    Returns:
        bool: True if a viewer was running."""
def viewscreen_consoles (ship):
    """The main-screen consoles of one ship - the audience every shot addresses.
    
    Narrowed to the SHIP's own screens, which is what keeps one bridge's viewer out of
    another's. Returns an empty set when no main screen is connected, which is normal
    and not an error."""
def viewscreen_framing (subject):
    """``(near, far)`` lens distances for a subject.
    
    Scaled off the hull's own size, so a starbase and a fighter both fill the frame
    rather than one being a speck and the other clipping the lens. ``exclusion_radius``
    is the only size the engine actually exposes; when it says nothing, a default that
    frames a mid-sized ship is better than a guess that frames nothing."""
def viewscreen_helm_override (ship, view, facing, mode):
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
        bool: True if a viewer was stood down."""
def viewscreen_home_ship (client_id):
    """The ship a console BELONGS to, even while a shot has it assigned elsewhere.
    
    Anything that means "this console's own ship" must ask this rather than
    ``sbs.get_ship_of_client``, which during a shot answers with the subject."""
def viewscreen_is_live (ship):
    """Whether a console is currently driving this ship's main screen."""
def viewscreen_label_for (mode):
    """The drop-down label for a mode, so a repaint re-selects what is running."""
def viewscreen_mode (ship):
    """The shot this ship's main screen is running, or ``"off"``."""
def viewscreen_mode_for (label):
    """The mode a drop-down label means. Unknown labels read as ``off`` - a console
    showing something we do not recognize must not leave the screen commandeered."""
def viewscreen_pages (subject, ship):
    """``[(name, markdown), ...]`` for this subject - empty pages dropped.
    
    A page that raises is skipped rather than taking the column down with it: one
    mission page with a bad key must not blank the whole viewer."""
def viewscreen_reset ():
    """Drop every running shot WITHOUT touching the engine - for mission reset.
    
    The tick tasks are already gone by then (``TickDispatcher.clear()``), and the
    clients these records name belong to a sim that is being torn down, so re-assigning
    their cameras is at best pointless. This just stops the records outliving the
    mission that made them."""
def viewscreen_set (ship, mode, subject=None):
    """Point this ship's main screen at something.
    
    Args:
        ship (Agent | int): the player ship whose screen this is.
        mode (str): one of ``MODES``. ``"off"`` is the same as ``viewscreen_clear``.
        subject (Agent | int, optional): what the shot is about - normally the science
            selection. ``None`` means no subject.
    
    Returns:
        bool: True when the state changed."""
def viewscreen_shot_props (current=None):
    """The whole property string for a shot drop-down.
    
    The list key is ``list:``, NOT ``items:`` - a dropdown built with the wrong key has
    no options to render and the engine dies allocating for it (`MemoryError: bad
    allocation`), which does not look like a typo from the outside. ``text:`` is the
    label shown while it is closed, so pass what is currently running."""
def viewscreen_subject (ship):
    """The id the shot is about, or 0."""
