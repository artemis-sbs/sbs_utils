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
def _apply_held (ship_id):
    """Fire the crew request that was parked behind a story claim, if any."""
def _claim_for (ship_id, tier, owner):
    """Take the claim, capturing the crew's state on the way in.
    
    ONE capture, covering the engine triple AND every main screen's home ship.
    Those used to be recorded by two different functions on two different
    triggers - the triple here, the homes inside ``viewscreen_apply`` and only on
    its 3D branch - which is a large part of why "what the crew had" kept going
    missing."""
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
def _remember_home (ship_id, cids):
    """Record each console's own ship before a shot takes the assignment away.
    
    The VALUE goes on the console, because `viewscreen_home_ship(client_id)` has
    only a client id to work with. The MEMBERSHIP goes on the ship, because a
    restore has to reach consoles that have since stopped being this ship's main
    screens - a console that changed console mid-shot still needs its ship back."""
def _restore_home (cids):
    """Give each console its own ship back.
    
    A home that no longer exists is dropped rather than re-assigned. It can be a
    camera object rather than a player ship - a Game Master or Director console
    rides one deliberately - and one deleted between capture and restore would be
    re-assigned in silence by the mock while the real engine falls back to its own
    default view."""
def _stand_down (ship_id, restore):
    """Tear the shot down. The claim is already dropped by the time this runs."""
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
    """Clear one slot (or all slots if ``slot`` is None) on the ``to`` targets.
    
    Taking a card down means taking it down, including for anyone who has not
    arrived yet - otherwise the catch-up would put it straight back. But only
    for the consoles actually named: a record the cleared consoles fully account
    for is retired, a wider one keeps running for everybody else."""
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
def viewscreen_baseline (ship):
    """The ``(view, facing, mode)`` the crew had before anyone took the screen."""
def viewscreen_baseline_drop (ship):
    """Forget the baseline without restoring it.
    
    What a helm takeover does: helm's choice IS the new state, so there is nothing
    to go back to and leaving a stale baseline recorded would let a later,
    unrelated release put the crew's screen somewhere they left minutes ago."""
def viewscreen_claim (ship, tier='console', owner=None, baseline=None, cids=None):
    """Record that ``owner`` holds this ship's main screen.
    
    Bookkeeping only - it does not move a camera or write a main-screen view. The
    caller (``viewscreen_set``, a cutscene, the Director) does that; this decides
    whether it is allowed to and remembers what to go back to.
    
    Args:
        ship: the player ship whose screen this is.
        tier (str): ``"console"`` or ``"story"``.
        owner (str, optional): the token from ``viewscreen_owner_token``. An
            unnamed claim is still a claim.
        baseline (tuple, optional): the ``(view, facing, mode)`` to record if this
            is the first claim. Captured by the caller because only it can read the
            engine state.
        cids (iterable, optional): the main screens whose home ship the caller has
            recorded, noted alongside the baseline on the first claim.
    
    Returns:
        bool: True if the claim was taken. False when a STORY claim holds and this
        is a console one - the caller should park its request rather than act."""
def viewscreen_claim_drop (ship, owner=None, keep_baseline=False):
    """Give up the claim. Bookkeeping only - see ``viewscreen_restore``.
    
    Args:
        owner (str, optional): refuse unless this token still holds it. ``None``
            forces, which is what a mission reset and the one-door console
            transition want.
        keep_baseline (bool): leave the baseline recorded. Only ``True`` while a
            caller is in the middle of applying it.
    
    Returns:
        bool: True if a claim was dropped."""
def viewscreen_claimed (ship):
    """Whether anything holds this ship's main screen."""
def viewscreen_clear (ship, owner=None):
    """Hand the screen back, restoring the view the crew had before it was taken.
    
    Args:
        owner (str, optional): refuse unless this token still holds the claim, so
            a console whose shot was replaced cannot take the screen off whoever
            replaced it. ``None`` forces.
    
    Returns:
        bool: True if a viewer was running."""
def viewscreen_console_enter (client_id):
    """A main screen is arriving. Record where it belongs, before anything moves it.
    
    THE FIRST LINE of any main-screen label. A shot ASSIGNS its console to the
    subject, so a console that takes its post while one is already running has no
    record of its own ship and nothing can give it back - and there is exactly one
    moment when the answer is still available, which is before this console is
    assigned anywhere.
    
    Cheap and idempotent: a console that already has a home recorded is left alone,
    so putting this at the top of a label that repaints constantly costs nothing.
    
    Returns:
        int | None: the ship this console belongs to."""
def viewscreen_consoles (ship):
    """The main-screen consoles of one ship - the audience every shot addresses.
    
    Narrowed to the SHIP's own screens, which is what keeps one bridge's viewer out of
    another's. Returns an empty set when no main screen is connected, which is normal
    and not an error."""
def viewscreen_crew_holds (ship):
    """Is the crew's own control still holding the screen against the consoles?"""
def viewscreen_crew_lock_remaining (ship):
    """Seconds left before a console may claim the screen again, or 0.0.
    
    A console can show this rather than silently doing nothing when a pick does
    not take."""
def viewscreen_crew_release (ship):
    """End the cooldown early - a console claim may take the screen again."""
def viewscreen_crew_took (ship):
    """The crew took the screen with their own control - start the cooldown."""
def viewscreen_dial_label (ship, owner):
    """What an "On Screen" drop-down should read, for the console that owns ``owner``.
    
    **The running shot only when it is OURS, otherwise "Off".** The dial is this
    console's control, not a status light for the ship: showing "On Screen - Orbit"
    because WEAPONS put something up invites science to think they are driving,
    and picking Off on it would then be refused - so the dial would be advertising
    an action it cannot take.
    
    One function rather than the expression written out on each console, so the two
    cannot drift, the same reason ``viewscreen_shot_props`` lives here."""
def viewscreen_effective_state (ship):
    """What this ship's main screen is ACTUALLY set to, after arbitration.
    
    ``handlerhooks`` writes the crew's triple, then asks
    ``viewscreen_helm_override`` what to do with it, and then fans a reroute out to
    the ship's main screens carrying the EVENT's values as task variables. When a
    story claim refused the press, those values are the rejected ones - so the
    reroute has to carry this instead, or a console reading the injected
    ``MAIN_SCREEN_VIEW`` sees a view the library declined to apply.
    
    LegendaryMissions reads the ship's inventory rather than the injected variable,
    so LM would not show this - which is exactly what makes it easy to ship broken."""
def viewscreen_framing (subject):
    """``(near, far)`` lens distances for a subject.
    
    Scaled off the hull's own size, so a starbase and a fighter both fill the frame
    rather than one being a speck and the other clipping the lens. ``exclusion_radius``
    is the only size the engine actually exposes; when it says nothing, a default that
    frames a mid-sized ship is better than a guess that frames nothing."""
def viewscreen_helm_override (ship, view, facing, mode, client_id=None):
    """Helm or weapons touched the engine's main-screen control.
    
    Called from the ``main_screen_change`` handler with the triple the engine just
    reported. What happens next depends on WHO holds the screen:
    
    * **A console claim** - science's "on screen", weapons', docking's - stands
      down, and nothing is restored: helm's choice IS the new state, and putting a
      recorded "before" back over the top would undo the very change being handled.
      Any request parked behind a story beat is thrown away too; helm just spoke,
      and a stale drop-down pick firing later would override the officer who
      overrode it.
    * **A story claim** - a cutscene, a hail, a mission beat - does NOT stand down.
      The crew's press is PARKED and applied when the story releases, so it is
      honored a few seconds late rather than lost, and the story's own triple is
      written back so the engine and the record agree again.
    
    **WHO pressed decides, not what the values are.** Only helm and weapons carry
    the ``main_screen_control`` widget; a main screen's widget list is
    ``3dview^ship_data`` / ``2dview^ship_data``, so a main screen cannot press one
    at all - every ``main_screen_change`` carrying a main screen's client id is
    that screen reporting back what we set it to. So an event from one of this
    ship's main screens is never a takeover, and an event from anywhere else
    always is.
    
    Comparing the reported triple against ``VIEWER_EXPECT`` instead was wrong in
    both directions, and each cost a real bug:
    
    * **The dial forces the view back to 3D.** Touching FRONT or CHASE means "show
      me that camera", so during a 3D shot it sends ``("3d_view", facing, mode)``
      - which is exactly what the shot recorded. Helm's press was read as a replay
      and swallowed; the engine moved the camera anyway (the flash), and the shot
      that was never stood down re-aimed it a moment later. Reported as science
      stealing the screen back.
    * **The shot cancelled itself.** Every shot goes through
      ``gui_cinematic_full_control``, which calls ``set_main_view_modes(cid,
      "3dview", "front", "cinematic")``. Coming back as an event that matches
      nothing, it read as a takeover - the viewer's own camera standing the viewer
      down.
    
    ``client_id=None`` keeps the old value comparison, for a caller that cannot say
    who pressed.
    
    The triple is written here as well as by the caller. ``handlerhooks`` already
    records it (issue #595) and writing it twice is harmless - but a function whose
    postcondition depends on the caller having gone first is a trap for the next
    caller, so this one leaves the ship in the state it was told about either way.
    On the story path that means writing the story's triple BACK over what the
    caller just recorded, which is the whole point.
    
    Returns:
        bool: True if a claim was stood down. False for a story claim that held -
        see ``viewscreen_effective_state`` for what the screen is actually showing
        afterwards, which is what the reroute has to carry."""
def viewscreen_hold (ship, request):
    """Park a crew request that arrived while a story held the screen.
    
    ONE request, not a queue: the crew pressing three things during a cutscene
    means they want the last one, and replaying all three on release would walk the
    screen through states nobody asked to see."""
def viewscreen_hold_drop (ship):
    """Throw the parked request away.
    
    What helm's control does on a console-tier claim: helm just spoke, and a stale
    drop-down pick firing later would override the officer who overrode it."""
def viewscreen_hold_take (ship):
    """Take the parked request, clearing it. Returns None when there is none."""
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
def viewscreen_owner (ship):
    """Who holds this ship's main screen, or ``""``."""
def viewscreen_owns (ship, owner):
    """Is ``owner``'s claim still the live one?
    
    The question a console should ask before acting on the screen it thinks it is
    driving. LegendaryMissions' weapons console hand-rolled this as a private
    ``WEAP_VIEWER_SUBJECT`` inventory value, and science never asked at all - which
    is why science re-pointing on a new selection used to yank a shot weapons had
    set up."""
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
def viewscreen_restore (ship, owner=None):
    """THE DOOR HOME. Put this ship's main screen back the way the crew had it.
    
    Drops the claim, stops the shot, takes the viewer's own overlays down, gives
    every main screen its own ship back, restores the baseline view, and then -
    and only then - applies whatever crew request was parked behind a story beat.
    
    The ORDER is load-bearing, twice:
    
    * **Assignments before the triple.** The assignment decides what a console can
      SEE; the triple only decides its widget list. Restore the triple first and
      the main-screen label re-runs while the console is still riding the subject,
      so it picks its widgets from the SUBJECT's ``MAIN_SCREEN_VIEW`` - the hazard
      ``gui_console`` documents.
    * **The parked request last.** Applying it claims the screen again and
      captures a baseline; it has to capture the RESTORED one, not the story's.
    
    Args:
        owner (str, optional): refuse unless this token still holds the claim.
            ``None`` forces - what a console transition and a reset want.
    
    Returns:
        bool: True if anything was holding the screen."""
def viewscreen_revision (client_id):
    """A number that changes whenever this console's ship hands the screen over.
    
    What a console watches with ``on change`` so a drop-down showing "On Screen -
    Orbit" repaints to "Off" the moment somebody else takes the screen, instead of
    lying about what is on it.
    
    ``on change``, not ``on signal``: a GUI task sitting in ``await gui()`` does not
    repaint because a signal fired - the same reason ``hail_console_revision``
    exists and is polled."""
def viewscreen_roster (ship):
    """The main screens that have a home recorded for this claim.
    
    Held on the SHIP while the home VALUE is held on each console, and that split
    is deliberate: ``viewscreen_home_ship(client_id)`` has only a client id, so the
    value has to be reachable from one - but a restore has to reach consoles that
    have since stopped being this ship's main screens, so the membership has to
    live somewhere that outlives the role."""
def viewscreen_roster_add (ship, client_id):
    """Note that this console has a home recorded - the late-joiner path."""
def viewscreen_seq (ship):
    """The claim sequence, bumped on every claim and every release.
    
    Poll it to notice the screen changed hands. Bumped BEFORE the outcome runs, the
    same rule ``hail.py`` follows, so a second actor in the same frame is already
    carrying a stale value by the time it arrives."""
def viewscreen_set (ship, mode, subject=None, owner=None, tier='console'):
    """Point this ship's main screen at something.
    
    Args:
        ship (Agent | int): the player ship whose screen this is.
        mode (str): one of ``MODES``. ``"off"`` is the same as ``viewscreen_clear``.
        subject (Agent | int, optional): what the shot is about - normally the science
            selection. ``None`` means no subject.
        owner (str, optional): the claim token, from ``viewscreen_owner_token``.
            Without one the claim is anonymous - still a claim, but nothing can
            ask whether it is still theirs.
        tier (str): ``"console"`` (the default - a crew member's pick) or
            ``"story"`` (a cutscene, a hail, a mission beat).
    
    Returns:
        bool: True when the state changed.
    
    **False now means three things.** It has always meant "already showing exactly
    that"; it also means "a STORY claim holds the screen, so your request was
    PARKED and will be applied when the story releases", and "the crew's own
    control has the screen for another moment" (``CREW_LOCK_SECONDS``). Ask
    ``viewscreen_owns(ship, owner)`` when you need to know which - that is the
    question a console actually has.
    
    **NEVER CALL THIS FROM A REPAINT PATH UNLESS ``viewscreen_owns`` IS TRUE.**
    The idempotent no-op above requires mode AND subject AND owner to match, so two
    consoles that both re-assert on repaint never hit it - their tokens differ - and
    they will ping-pong at GUI-tick rate, each claim bumping the sequence that makes
    the other repaint. The library cannot break that cycle for you; the crew
    cooldown damps it, but the guard is the caller's. LegendaryMissions' consoles
    are the worked example: every automatic re-point is behind ``viewscreen_owns``,
    and only a human press calls this unguarded."""
def viewscreen_shot_props (current=None):
    """The whole property string for a shot drop-down.
    
    The list key is ``list:``, NOT ``items:`` - a dropdown built with the wrong key has
    no options to render and the engine dies allocating for it (`MemoryError: bad
    allocation`), which does not look like a typo from the outside. ``text:`` is the
    label shown while it is closed, so pass what is currently running."""
def viewscreen_subject (ship):
    """The id the shot is about, or 0."""
def viewscreen_take (ship, owner=None, tier='story'):
    """Claim this ship's main screen WITHOUT starting one of the viewer's own shots.
    
    For anything that drives the screen its own way and still has to be arbitrated:
    a cutscene, the Director, a mission beat pointing the camera by hand. It records
    the crew's view and every main screen's home ship the same way ``viewscreen_set``
    does, so ``viewscreen_restore`` puts the bridge back afterwards - which is what
    a cutscene played during a science shot could not do before, because the only
    thing that captured a baseline was a shot starting.
    
    Returns:
        bool: False when a story claim already holds the screen and this is a
        console-tier request."""
def viewscreen_tier (ship):
    """``"console"``, ``"story"``, or ``""`` when nothing holds the screen."""
def viewscreen_view_modes (client_id, ship_id=None):
    """The ``(view, facing, mode)`` a main screen should hand ``set_main_view_modes``.
    
    The view and facing belong to the SHIP - one bridge, one screen state. The
    camera MODE does not, quite: the engine reports ``"cinematic"`` while a script
    is driving that client's camera, and because the three arrive together that
    value lands in the ship's record and every other main screen on the bridge then
    reads it as its own.
    
    So the mode is remembered PER CONSOLE and substituted whenever the ship's copy
    says ``"cinematic"``. LegendaryMissions carried this as a task-local
    ``default my_mode = "chase"``, which is per GUI TASK rather than per console -
    so every reroute reset it, and a screen the crew had put in ``first_person`` or
    ``tracking`` silently snapped back to ``chase``.
    
    Returns:
        tuple: ``(view, facing, mode)``, ready to pass straight through."""
