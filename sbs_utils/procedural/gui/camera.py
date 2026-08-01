"""Mission-facing camera control.

The engine's whole camera API is one call - `cinematic_control(clientID,
scriptControlsCamera, dollyID, dollyPos, targetID, targetPos)` - wrapped by
`gui_cinematic_full_control`. It takes a single client id, which is the awkward part: the
rest of the procedural layer addresses audiences as sets (`role("mainscreen") & role("tsn")`),
so a mission that does not happen to know a client id has to invent an indirection to use it.

These are that missing layer, and nothing more. They add no behavior the engine does not
already have; they make the one call addressable, and they carry the placement rules that are
otherwise learned by getting a black screen.

FOUR FACTS ABOUT THE ENGINE CAMERA, all of them load-bearing:

* **A camera IS an object.** The lens sits at an object's position plus an offset. Every
  camera move is therefore an object move, and there is no interpolation, FOV, roll or shake.
* **The offsets are WORLD-space, not object-local.** LM's Game Master orbits its 3D view by
  rotating the offset vector itself before passing it in
  (`Vec3(0,0,d).rotate_around(...)`, gamemaster.mast) - which it would not need to do if the
  engine rotated offsets into the dolly's frame. `camera_orbit_eye` below is that formula.
* **The console must be ASSIGNED to the object the camera rides.** Engine-observed: a camera
  change only takes when the client is assigned to the dolly. Re-pointing alone left a black
  screen, and so did moving the object the lens was already on; assigning and then pointing
  worked. So `camera_track` assigns for you - the two are one operation, not two.

  This contradicts a reading of the Game Master, which points at selected objects it is not
  assigned to. Something there is still unaccounted for - possibly that it re-issues every few
  seconds regardless - but the observed behavior wins over the inference.
* **A camera on a SHIP at zero offset is inside its hull.** Only an invisible anchor is safe
  at (0,0,0). `camera_anchor` makes one.
* **The dolly and the target must be the SAME object.** Two different ids render a black
  frame. `camera_track` folds a two-object request into the one-object shape for you, keeping
  the lens exactly where it was asked for - see `camera_shot`, which is the same idea stated
  positively.
* **The lens must not sit ON its look-at point.** A zero-length view vector has no direction
  to face; the frame is black. `camera_track` nudges such a pin apart rather than emit it.
"""
from ...helpers import FrameContext
from ...vec import Vec3
from .cinematic import gui_cinematic_auto, gui_cinematic_full_control
from .overlay import consoles_of


def _vec(v):
    """Accept a Vec3, a 3-tuple/list, or None (meaning no offset)."""
    if v is None:
        return Vec3(0, 0, 0)
    if isinstance(v, Vec3):
        return v
    return Vec3(float(v[0]), float(v[1]), float(v[2]))


# A camera this close to its own look-at point has no usable view direction. Small enough to
# be a nudge rather than a reframe, large enough that normalize() is well conditioned.
MIN_SEPARATION = 50.0


def _xyz(v):
    return (float(v.x), float(v.y), float(v.z))


def _degenerate(dolly_id, eye, target_id, look):
    """True when the camera would sit exactly on the point it is aimed at.

    Same object and identical offsets is the common way in; two different objects that happen
    to share a position is the rarer one, and is checked too because the symptom is identical.
    """
    from ..query import to_object
    ex, ey, ez = _xyz(eye)
    lx, ly, lz = _xyz(look)
    if dolly_id == target_id:
        return (ex, ey, ez) == (lx, ly, lz)
    a = to_object(dolly_id)
    b = to_object(target_id)
    if a is None or b is None:
        return False
    dx = (a.pos.x + ex) - (b.pos.x + lx)
    dy = (a.pos.y + ey) - (b.pos.y + ly)
    dz = (a.pos.z + ez) - (b.pos.z + lz)
    return (dx * dx + dy * dy + dz * dz) < 1e-6


def camera_anchor(x, y, z, name="", roles="camera_anchor"):
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
        int: the anchor's id, or 0 if it could not be spawned.
    """
    from ..spawn import player_spawn
    from ..query import to_object, to_id
    from ..roles import remove_role
    cam = to_object(player_spawn(x, y, z, name, f"#,{roles}", "invisible"))
    if cam is None:
        return 0
    remove_role(cam, "__player__")
    return to_id(cam)


def camera_assign(to, obj, consoles=None):
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
        int: how many consoles were assigned.
    """
    from ..query import to_id
    oid = to_id(obj)
    if not oid:
        return 0
    sbs = FrameContext.context.sbs
    n = 0
    for cid in consoles_of(to, consoles):
        sbs.assign_client_to_ship(cid, oid)
        n += 1
    return n


def camera_track(to, dolly, eye=None, target=None, look=None, consoles=None):
    """Point one or more consoles' cinematic camera at a subject.

    Camera sits at ``dolly`` + ``eye``; it looks at ``target`` + ``look``. Both offsets are
    WORLD-space (see the module docstring), so an offset does not rotate as the dolly turns -
    use `camera_orbit_eye` to place a shot by angle, and recompute it when you want the angle
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
            SHIP with no ``eye`` offset puts the lens inside its hull.
        eye (Vec3 | tuple, optional): offset from the dolly. Defaults to no offset.
        target (optional): what to look at. Defaults to the dolly.
        look (Vec3 | tuple, optional): offset from the target. Defaults to no offset.
        consoles (str, optional): narrow to consoles carrying these roles.

    Returns:
        int: how many consoles were pointed.

    Example:
        cam = camera_anchor(0, 900, -2600)
        camera_assign(role("mainscreen"), cam)
        camera_track(role("mainscreen"), cam, target=hero_ship)
    """
    from ..query import to_id
    dolly_id = to_id(dolly)
    if not dolly_id:
        return 0
    target_id = to_id(target) if target is not None else dolly_id
    eye_v = _vec(eye)
    look_v = _vec(look)

    # ENGINE CONSTRAINT: the dolly and the target must be the SAME object. Naming two
    # different ones renders a black frame - confirmed with everything else held constant
    # (CameraRepro rungs 10 and 11: identical offsets, one id draws, two ids do not).
    #
    # It costs nothing, because the offsets are world-space: keep the TARGET (what the shot is
    # about) and re-express the lens as an offset from it. The resulting shot is the one that
    # was asked for, in the only shape that draws.
    if target_id != dolly_id:
        from ..query import to_object
        d = to_object(dolly_id)
        t = to_object(target_id)
        if d is not None and t is not None:
            lens_x = d.pos.x + eye_v.x
            lens_y = d.pos.y + eye_v.y
            lens_z = d.pos.z + eye_v.z
            eye_v = Vec3(lens_x - (t.pos.x + look_v.x),
                         lens_y - (t.pos.y + look_v.y),
                         lens_z - (t.pos.z + look_v.z))
            dolly_id = target_id
            look_v = Vec3(0.0, 0.0, 0.0)
        else:
            dolly_id = target_id

    # A camera placed exactly where it is looking has no direction to face: the renderer's
    # `normalize(target - eye)` divides by a zero length, there is no forward axis, and the
    # frame comes out BLACK with nothing logged anywhere. Engine-observed, and easy to ask for
    # by accident - `camera_track(to, cam)` with no offset is exactly this, since `target`
    # defaults to the dolly. Say so rather than let it look like a broken camera.
    if _degenerate(dolly_id, eye_v, target_id, look_v):
        from ...mast.mast import DEBUG
        DEBUG("[camera] camera_track: the camera was AT the point it is looking at "
              f"(dolly {dolly_id} + {tuple(_xyz(eye_v))} == target {target_id} + "
              f"{tuple(_xyz(look_v))}). Nudged back by {MIN_SEPARATION}u so it draws - give "
              "`eye` a real offset to frame it deliberately.")
        eye_v = Vec3(eye_v.x, eye_v.y, eye_v.z - MIN_SEPARATION)

    sbs = FrameContext.context.sbs
    n = 0
    for cid in consoles_of(to, consoles):
        sbs.assign_client_to_ship(cid, dolly_id)
        gui_cinematic_full_control(cid, dolly_id, eye_v, target_id, look_v)
        n += 1
    return n


def camera_shot(to, subject, eye_world, consoles=None):
    """Put the lens at an ABSOLUTE world position, looking at `subject`.

    The natural way to write a shot - "camera over here, pointed at that" - is to pass two
    different objects as dolly and target. That shape does not render (see CINEMATIC_PLAN.md
    section 0); what renders is one object named twice, with the lens offset away from it,
    which is what the Game Master does.

    That constraint costs nothing, because the offsets are WORLD-space: any camera position is
    reachable as `wanted - subject.pos`. So this composes the shot you meant out of the shape
    the engine accepts, and it keeps working as the subject moves, since the offset is
    recomputed from wherever it is at the time.

    Args:
        to: audience (see ``consoles_of``).
        subject: the object to look at - and, necessarily, the one the lens rides.
        eye_world (Vec3 | tuple): where the camera should BE, in world coordinates.
        consoles (str, optional): narrow to consoles carrying these roles.

    Returns:
        int: how many consoles were pointed.

    Example:
        camera_shot(role("mainscreen"), hero_ship, Vec3(0, 900, -2600))
    """
    from ..query import to_object
    subj = to_object(subject)
    if subj is None:
        return 0
    want = _vec(eye_world)
    offset = Vec3(want.x - subj.pos.x, want.y - subj.pos.y, want.z - subj.pos.z)
    return camera_track(to, subject, eye=offset, target=subject, consoles=consoles)


def camera_auto(to=None, consoles=None):
    """Hand the camera back to the engine's own director (it follows the assigned ship).

    The release path for anything `camera_track` took over - end a cutscene with this.

    Args:
        to: audience (see ``consoles_of``); ``None`` is the current console.
        consoles (str, optional): narrow to consoles carrying these roles.

    Returns:
        int: how many consoles were released.
    """
    n = 0
    for cid in consoles_of(to, consoles):
        gui_cinematic_auto(cid)
        n += 1
    return n


def camera_orbit_eye(distance, yaw=0.0, pitch=0.0):
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
        Vec3: the offset to pass as ``eye``.

    Example:
        camera_track(role("mainscreen"), cam, eye=camera_orbit_eye(1800, yaw=35, pitch=20),
                     target=hero_ship)
    """
    return Vec3(0, 0, float(distance)).rotate_around(Vec3(0, 0, 0), float(pitch), float(yaw), 0)
