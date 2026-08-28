from sbs_utils.helpers import FrameContext
def _cutscene_bridges (cids):
    """The PLAYER SHIPS whose main screens this cutscene is playing to.
    
    viewscreen_home_ship, not get_ship_of_client - a console mid-shot is riding the
    contact it is filming. And player ships only: a Game Master or Director console
    rides a detached camera object deliberately, and a claim on one of those would
    be bookkeeping about a bridge that does not exist."""
def _warn_unknown_shot_keys (shot):
    """One warning naming any key `shot_apply` will ignore."""
def camera_assignment (to=None, consoles=None):
    """What each console is riding right now: ``{client_id: ship_id}``.
    
    Taken BEFORE a cutscene so it can be given back afterwards. `camera_track` ASSIGNS a
    console to the object the lens rides, and assignment is identity, not framing: it
    decides what that console can see and what the engine director follows once the
    camera is released. So a shot that rode a station leaves the mainscreen watching
    that station, and `camera_auto` alone does not undo it - it hands control back to a
    director that dutifully keeps following the wrong ship.
    
    Captured per console rather than assumed to be "the player ship", because it is not
    always one: a Game Master or Admiral console rides a detached camera object, and
    putting it back on a player ship would be a worse bug than the one being fixed.
    
    Returns:
        dict: client id -> the ship id it was assigned to. Ids that read back as 0 are
        omitted; there is nothing to restore and re-assigning to 0 would detach it."""
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
def camera_move (to, subject, lens_from, lens_to, seconds, ease='in_out', consoles=None):
    """Glide the lens from one world position to another, looking at `subject`.
    
    Args:
        to: audience (see ``consoles_of``).
        subject: what the shot looks at - and, necessarily, what the lens rides.
        lens_from (Vec3 | tuple): world position to start at.
        lens_to (Vec3 | tuple): world position to end at.
        seconds (float): duration.
        ease (str): ``in_out`` (default), ``in``, ``out`` or ``linear``. Ours - the
            engine interpolates nothing.
    
    Returns:
        Promise: resolves with the final lens position when the move ends.
    
    Example:
        await camera_move(role("mainscreen"), hero, Vec3(0,900,-4000), Vec3(0,300,-900), 6)"""
def camera_move_stop (to=None, consoles=None):
    """Stop any running move on these consoles, leaving the lens where it is.
    
    Called for you by every move below: two drivers re-aiming the same console
    would fight tick by tick, and the symptom (a camera that jitters between two
    paths) reads as an engine bug rather than a second caller."""
def camera_orbit_lens (distance, yaw=0.0, pitch=0.0):
    """The offset for a shot ``distance`` away at a given angle, as a world-space Vec3.
    
    This is LM's Game Master formula, which is the reference implementation of an orbit here:
    take a vector straight back and rotate it. Because the engine does not rotate offsets into
    the dolly's frame, orbiting means recomputing this and calling `camera_track` again - which
    is exactly what the GM does when you drag its orbit slider.
    
    Args:
        distance (float): how far from the subject.
        yaw (float, optional): degrees around the subject.
        pitch (float, optional): degrees above (positive) or below it.
    
    Returns:
        Vec3: the offset to pass as ``lens``.
    
    Example:
        camera_track(role("mainscreen"), cam, lens=camera_orbit_lens(1800, yaw=35, pitch=20),
                     target=hero_ship)"""
def camera_restore (assignments):
    """Put each console back on the object it was riding, and release the camera.
    
    The counterpart to `camera_assignment`, and the general rule for ending a cutscene:
    give the console back its own ship, THEN hand the camera to the engine director. In
    that order - releasing first leaves the director following the shot subject for the
    frames in between.
    
    Args:
        assignments (dict): what `camera_assignment` returned.
    
    Returns:
        int: how many consoles were put back."""
def camera_shot (to, subject, lens_world, consoles=None):
    """Put the lens at an ABSOLUTE world position, looking at `subject`.
    
    The natural way to write a shot - "camera over here, pointed at that" - is to pass two
    different objects as dolly and target. That shape does not render (see
    DESIGN_RECORD.md s7); what renders is one object named twice, with the lens offset away from it,
    which is what the Game Master does.
    
    That constraint costs nothing, because the offsets are WORLD-space: any camera position is
    reachable as `wanted - subject.pos`. So this composes the shot you meant out of the shape
    the engine accepts, and it keeps working as the subject moves, since the offset is
    recomputed from wherever it is at the time.
    
    Args:
        to: audience (see ``consoles_of``).
        subject: the object to look at - and, necessarily, the one the lens rides.
        lens_world (Vec3 | tuple): where the camera should BE, in world coordinates.
        consoles (str, optional): narrow to consoles carrying these roles.
    
    Returns:
        int: how many consoles were pointed.
    
    Example:
        camera_shot(role("mainscreen"), hero_ship, Vec3(0, 900, -2600))"""
def consoles_of (to, consoles=None):
    """Resolve an audience expression to a set of console client ids.
    
    Args:
        to: ``None`` (the current console), a client id, a ship id/object, a side
            key or side agent, or a set/list mixing any of those.
        consoles (str, optional): narrow to consoles with these roles, e.g.
            ``"mainscreen"`` or ``"science, comms"``.
    
    Returns:
        set[int]: console client ids (possibly empty)."""
def cutscene_define (name, shots, letterbox=True, skippable=True, bar=4, release=True):
    """Register a cutscene under ``name``.
    
    Args:
        name (str): what ``cutscene_play`` will look up.
        shots (list[dict]): in order. Per shot:
            ``subject`` (required) - what the shot looks at, and necessarily what
            the lens rides; ``framing`` (``close``/``medium``/``wide``, or a two-item
            list for a move) OR ``lens`` (world position) OR ``move`` ([from, to]);
            ``seconds`` (default 4); ``ease``; ``yaw``/``pitch``; ``overlay``
            ({"kind": ..., plus that kind's fields}).
            Prefer ``framing``: it scales to the subject's hull, so one shot frames a
            runabout and a starbase alike. ``lens``/``move`` are world POSITIONS and
            so also depend on where the subject is parked.
        letterbox (bool): black bars for the duration.
        skippable (bool): whether ``cutscene_skip`` ends it.
        bar (float): letterbox bar height in em.
        release (bool): at the end, put each console back on the object it was riding
            and hand the camera to the engine's director.
            Leave it True unless the next thing the story does is set its own shot -
            a cutscene that ends still holding a dolly will drop to the engine
            default the moment that object is deleted.
    
    Returns:
        dict: the stored cutscene."""
def cutscene_framing (subject, size='medium'):
    """How far the lens sits for a named shot size, scaled to the subject's own hull.
    
    A DISTANCE TYPED BY HAND FRAMES EXACTLY ONE SHIP. The subjects a mission points a
    camera at are not one size: across the TNG pack a B'Rel is 25 units of hull radius
    and Deep Space Nine is 220, and a planet is 10,000. One coordinate triple makes the
    big one overflow the frame and the small one a speck, which is precisely the report
    this exists to answer.
    
    So the distance is read off the subject instead. `viewscreen_framing` already does
    that arithmetic - 6 hull radii at the closest, 16 at the widest, floored at 250 so
    the engine reporting a tiny hull cannot put the lens inside it - and the Director
    has framed its shots that way since it deleted its own distance sliders, on the
    grounds that "a fixed number framed a starbase and a fighter equally badly".
    
    `medium` is the midpoint rather than a fourth constant, so there is still exactly
    one place these numbers are written down.
    
    Args:
        subject: the object the shot looks at.
        size (str): ``close``, ``medium`` or ``wide``. Anything else is treated as
            ``medium`` - a misspelled size should give a usable shot, not no shot.
    
    Returns:
        float: distance from the subject, in world units."""
def cutscene_get (name):
    """The stored cutscene, or None."""
def cutscene_play (name_or_shots, to=None, consoles=None, **overrides):
    """Play a cutscene and return a Promise that resolves when it ends.
    
    Args:
        name_or_shots: a name from ``cutscene_define``, or a list of shots to play
            without registering one.
        to: audience (see ``consoles_of``).
        **overrides: any ``cutscene_define`` field, for this run only.
    
    Returns:
        Promise: resolves with ``{"skipped": bool, "shots": int, "name": str}``."""
def cutscene_playing (to=None, consoles=None):
    """Whether a cutscene is running on any of these consoles."""
def cutscene_skip (to=None, consoles=None):
    """Skip a running cutscene. Returns how many consoles were skipped.
    
    A no-op on a cutscene defined as unskippable, so a global skip button can be
    wired once and left alone."""
def cutscene_stop (to=None, consoles=None):
    """Stop a running cutscene without honouring ``skippable`` - the teardown path.
    
    Resolves its promise as skipped, so a story awaiting it still continues."""
def overlay_clear (slot=None, to=None, consoles=None):
    """Clear one slot (or all slots if ``slot`` is None) on the ``to`` targets.
    
    Taking a card down means taking it down, including for anyone who has not
    arrived yet - otherwise the catch-up would put it straight back. But only
    for the consoles actually named: a record the cleared consoles fully account
    for is retired, a wider one keeps running for everybody else."""
def overlay_kind (kind, to=None, consoles=None, slot=None, seconds=None, **fields):
    """Low-level front door: show any registered ``kind`` with its default slot.
    
    The escape hatch for callers that pick the kind at runtime (the quest driver's
    inline overlay directives, AMD records). Prefer the named wrappers when the
    kind is known at author time."""
def shot_apply (cids, shot):
    """Put one shot on these consoles. Returns its move Promise, or None.
    
    THE definition of a shot, shared by the cutscene sequencer and the rundown, so
    "a shot" means one thing in both: a subject, where the lens sits (or travels),
    and optional furniture. The slots it used come back on the returned set so a
    caller can clear exactly what it put up.
    
    A shot says where the lens goes in ONE of two ways:
    
    * ``framing`` - a named size (``close``/``medium``/``wide``), or a two-item list
      for a move (``["wide", "close"]`` is a push in). The distance is derived from the
      subject's hull, so the same shot frames a runabout and a starbase alike, and it
      does not depend on where either happens to be parked.
    * ``lens`` / ``move`` - literal WORLD POSITIONS, unchanged and still supported.
      Note these are positions, not offsets: a subject sitting 7,000 units from the
      origin is framed 7,000 units differently than the same shot at the origin, which
      is the trap `framing` exists to close."""
def shot_furniture (cids, shot):
    """Show a shot's overlay, if it has one. Returns the slots it used."""
def viewscreen_framing (subject):
    """``(near, far)`` lens distances for a subject.
    
    Scaled off the hull's own size, so a starbase and a fighter both fill the frame
    rather than one being a speck and the other clipping the lens. ``exclusion_radius``
    is the only size the engine actually exposes; when it says nothing, a default that
    frames a mid-sized ship is better than a guess that frames nothing."""
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
class _Playing(object):
    """One cutscene running on one set of consoles."""
    def __init__ (self, scene, cids, prom):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def advance (self):
        ...
    def finish (self, skipped):
        ...
    def start_shot (self, shot):
        ...
    def tick (self, _t):
        ...
