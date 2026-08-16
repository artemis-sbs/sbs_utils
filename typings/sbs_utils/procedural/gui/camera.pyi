from sbs_utils.helpers import FrameContext
from sbs_utils.vec import Vec3
def _degenerate (dolly_id, lens, target_id, look):
    """True when the camera would sit exactly on the point it is aimed at.
    
    Same object and identical offsets is the common way in; two different objects that happen
    to share a position is the rarer one, and is checked too because the symptom is identical."""
def _drive (to, consoles, subject, seconds, lens_at, ease='in_out'):
    """Run a shot whose lens position is a function of eased time.
    
    `lens_at(u)` returns the world position for eased progress `u`. Shared by every
    move below, because the only thing that differs between them is that function."""
def _ease (name, t):
    """Ours, because the engine has none. `t` is 0..1."""
def _now ():
    ...
def _vec (v):
    """Accept a Vec3, a 3-tuple/list, or None (meaning no offset)."""
def _xyz (v):
    ...
def camera_anchor (x, y, z, name='', roles='camera_anchor'):
    """Spawn an invisible camera post and return its id.
    
    The detached-camera pattern LM's Game Master already uses: a player-family object with the
    'invisible' art, with ``__player__`` removed so it is not a player ship. It has to be
    player-family rather than terrain because a client can be ASSIGNED to it, and it is
    invisible so it never appears in the shot it exists to frame.
    
    Args:
        x, y, z (float): where to put it.
        name (str, optional): display name; usually empty for a camera post.
        roles (str, optional): extra roles, comma separated.
    
    Returns:
        int: the anchor's id, or 0 if it could not be spawned."""
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
def camera_lens (to=None, consoles=None):
    """Where the lens is right now on the first of these consoles, or None.
    
    The mover records it, so a rack or a follow-on move can start from where the
    last one finished instead of the caller having to remember."""
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
def camera_rack (to, subject, consoles=None):
    """Look at something else WITHOUT moving the lens - a rack focus.
    
    Holds the current world position and re-aims at ``subject``. Any running move is
    stopped first: a rack during a move is a new intent, not a modifier on the old one.
    
    Returns:
        int: how many consoles were re-aimed."""
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
def camera_track (to, dolly, lens=None, target=None, look=None, consoles=None):
    """Point one or more consoles' cinematic camera at a subject.
    
    Camera sits at ``dolly`` + ``lens``; it looks at ``target`` + ``look``. Both offsets are
    WORLD-space (see the module docstring), so an offset does not rotate as the dolly turns -
    use `camera_orbit_lens` to place a shot by angle, and recompute it when you want the angle
    to change.
    
    ``target`` defaults to ``dolly``: a single-subject shot pins both ids to that object, which
    is the shape the engine expects.
    
    ASSIGNS each console to `dolly` before pointing, because the engine only honors the change
    when they match (see the module docstring). `camera_assign` remains for the rare case of
    setting a console's object without touching its camera.
    
    Note the consequence: moving the camera to an object CHANGES what that console can see,
    since view culling follows the assigned object. That is the engine's model, not a choice
    this wrapper makes.
    
    Args:
        to: audience - a client id, a ship, a side, or a set/role query (see ``consoles_of``).
        dolly: the object the camera rides (id or object). Prefer a `camera_anchor`; pinning a
            SHIP with no ``lens`` offset puts the lens inside its hull.
        lens (Vec3 | tuple, optional): offset from the dolly. Defaults to no offset.
        target (optional): what to look at. Defaults to the dolly.
        look (Vec3 | tuple, optional): offset from the target. Defaults to no offset.
        consoles (str, optional): narrow to consoles carrying these roles.
    
    Returns:
        int: how many consoles were pointed.
    
    Example:
        cam = camera_anchor(0, 900, -2600)
        camera_assign(role("mainscreen"), cam)
        camera_track(role("mainscreen"), cam, target=hero_ship)"""
def consoles_of (to, consoles=None):
    """Resolve an audience expression to a set of console client ids.
    
    Args:
        to: ``None`` (the current console), a client id, a ship id/object, a side
            key or side agent, or a set/list mixing any of those.
        consoles (str, optional): narrow to consoles with these roles, e.g.
            ``"mainscreen"`` or ``"science, comms"``.
    
    Returns:
        set[int]: console client ids (possibly empty)."""
def gui_cinematic_auto (client_id):
    """Switch a client to cinematic view, automatically tracking its assigned ship.
    
    Sets the client's view mode to ``"3dview/front/cinematic"`` with automatic
    camera control. The tracked ship must expose excitement values; player ships
    have these set automatically.
    
    Args:
        client_id (int): The client to switch to cinematic view.
    
    Example:
        gui_cinematic_auto(CLIENT_ID)"""
def gui_cinematic_full_control (client_id, camera_id, camera_offset, tracked_id, tracked_offset):
    """Switch a client to cinematic view with explicit camera and target control.
    
    Sets the view mode to ``"3dview/front/cinematic"`` and hands full camera
    control to the caller. Both offset vectors are converted to engine
    ``vec3`` objects before being passed to ``cinematic_control``.
    
    Args:
        client_id (int): The client to switch to cinematic view.
        camera_id (int): Object ID to use as the camera position anchor.
        camera_offset (Vec3 | None): Offset from ``camera_id`` in world units.
            Pass ``None`` to use the object's origin.
        tracked_id (int): Object ID for the camera to look at.
        tracked_offset (Vec3 | None): Offset from ``tracked_id`` to look at.
            Pass ``None`` to use the object's origin.
    
    Example:
        gui_cinematic_full_control(CLIENT_ID, camera_ship_id, Vec3(0,50,0), target_id, None)"""
