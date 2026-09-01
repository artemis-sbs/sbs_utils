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
  engine rotated offsets into the dolly's frame. `camera_orbit_lens` below is that formula.
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
import math

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


def _degenerate(dolly_id, lens, target_id, look):
    """True when the camera would sit exactly on the point it is aimed at.

    Same object and identical offsets is the common way in; two different objects that happen
    to share a position is the rarer one, and is checked too because the symptom is identical.
    """
    from ..query import to_object
    ex, ey, ez = _xyz(lens)
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


def camera_track(to, dolly, lens=None, target=None, look=None, consoles=None):
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
        camera_track(role("mainscreen"), cam, target=hero_ship)
    """
    from ..query import to_id
    dolly_id = to_id(dolly)
    if not dolly_id:
        return 0
    target_id = to_id(target) if target is not None else dolly_id
    eye_v = _vec(lens)
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
    # `normalize(target - lens)` divides by a zero length, there is no forward axis, and the
    # frame comes out BLACK with nothing logged anywhere. Engine-observed, and easy to ask for
    # by accident - `camera_track(to, cam)` with no offset is exactly this, since `target`
    # defaults to the dolly. Say so rather than let it look like a broken camera.
    if _degenerate(dolly_id, eye_v, target_id, look_v):
        from ...mast.mast import DEBUG
        DEBUG("[camera] camera_track: the camera was AT the point it is looking at "
              f"(dolly {dolly_id} + {tuple(_xyz(eye_v))} == target {target_id} + "
              f"{tuple(_xyz(look_v))}). Nudged back by {MIN_SEPARATION}u so it draws - give "
              "`lens` a real offset to frame it deliberately.")
        eye_v = Vec3(eye_v.x, eye_v.y, eye_v.z - MIN_SEPARATION)

    sbs = FrameContext.context.sbs
    n = 0
    for cid in consoles_of(to, consoles):
        sbs.assign_client_to_ship(cid, dolly_id)
        gui_cinematic_full_control(cid, dolly_id, eye_v, target_id, look_v)
        n += 1
    return n


def camera_shot(to, subject, lens_world, consoles=None):
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
        camera_shot(role("mainscreen"), hero_ship, Vec3(0, 900, -2600))
    """
    from ..query import to_object
    subj = to_object(subject)
    if subj is None:
        return 0
    want = _vec(lens_world)
    offset = Vec3(want.x - subj.pos.x, want.y - subj.pos.y, want.z - subj.pos.z)
    return camera_track(to, subject, lens=offset, target=subject, consoles=consoles)


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


def camera_assignment(to=None, consoles=None):
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
        omitted; there is nothing to restore and re-assigning to 0 would detach it.
    """
    # viewscreen_home_ship, NOT sbs.get_ship_of_client. While a viewscreen shot is
    # running a main screen is ASSIGNED TO THE SUBJECT - the engine only honors a
    # camera change when the console and the lens ride the same object - so the raw
    # call answers with the enemy being filmed. Capturing THAT as the console's home
    # is how a cutscene played during a shot left the main screen watching an enemy
    # ship permanently: camera_restore dutifully put it back where it was told.
    # Imported here rather than at module scope; viewscreen imports this module.
    from .viewscreen import viewscreen_home_ship
    held = {}
    for cid in consoles_of(to, consoles):
        try:
            oid = viewscreen_home_ship(cid)
        except Exception:                               # noqa: BLE001
            continue
        if oid:
            held[cid] = oid
    return held


def camera_restore(assignments):
    """Put each console back on the object it was riding, and release the camera.

    The counterpart to `camera_assignment`, and the general rule for ending a cutscene:
    give the console back its own ship, THEN hand the camera to the engine director. In
    that order - releasing first leaves the director following the shot subject for the
    frames in between.

    Args:
        assignments (dict): what `camera_assignment` returned.

    Returns:
        int: how many consoles were put back.
    """
    if not assignments:
        return 0
    sbs = FrameContext.context.sbs
    n = 0
    for cid, oid in assignments.items():
        if not oid:
            continue
        sbs.assign_client_to_ship(cid, oid)
        gui_cinematic_auto(cid)
        n += 1
    return n


def camera_orbit_lens(distance, yaw=0.0, pitch=0.0):
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
                     target=hero_ship)
    """
    return Vec3(0, 0, float(distance)).rotate_around(Vec3(0, 0, 0), float(pitch), float(yaw), 0)


# --- Phase 2: the mover ------------------------------------------------------
#
# "Camera animation" is a misnomer here. The engine has no interpolation, so a move
# is a driver that RE-AIMS the shot every tick - which the Game Master proves is
# fine (it re-applies its camera on every change and unconditionally every ~15s).
#
# Two engine facts shape all of this:
#   * offsets are WORLD-space, so an orbit is "recompute the offset and re-aim",
#     not "rotate a local frame". That is one driver task per moving shot.
#   * dolly and target must be the same object, so a move animates the LENS around
#     a subject. There is no second object to fly.
#
# Everything returns a Promise, so MAST can `await` a move or race it.

# client_id -> {"task", "lens" (world Vec3), "subject"}. Per CONSOLE, because two
# consoles can be running different shots at once.
_MOVES = {}


def camera_move_stop(to=None, consoles=None):
    """Stop any running move on these consoles, leaving the lens where it is.

    Called for you by every move below: two drivers re-aiming the same console
    would fight tick by tick, and the symptom (a camera that jitters between two
    paths) reads as an engine bug rather than a second caller.
    """
    n = 0
    for cid in consoles_of(to, consoles):
        state = _MOVES.pop(cid, None)
        if state is not None:
            task = state.get("task")
            if task is not None:
                task.stop()
            n += 1
    return n


def camera_lens(to=None, consoles=None):
    """Where the lens is right now on the first of these consoles, or None.

    The mover records it, so a rack or a follow-on move can start from where the
    last one finished instead of the caller having to remember.
    """
    for cid in consoles_of(to, consoles):
        state = _MOVES.get(cid)
        if state is not None:
            return state.get("lens")
    return None


def _ease(name, t):
    """Ours, because the engine has none. `t` is 0..1."""
    if t <= 0.0:
        return 0.0
    if t >= 1.0:
        return 1.0
    if name == "in":
        return t * t
    if name == "out":
        return 1.0 - (1.0 - t) * (1.0 - t)
    if name == "in_out":
        return 2.0 * t * t if t < 0.5 else 1.0 - 2.0 * (1.0 - t) * (1.0 - t)
    return t          # linear, and the fallback for an unknown name


def _now():
    return FrameContext.sim_seconds


def _drive(to, consoles, subject, seconds, lens_at, ease="in_out"):
    """Run a shot whose lens position is a function of eased time.

    `lens_at(u)` returns the world position for eased progress `u`. Shared by every
    move below, because the only thing that differs between them is that function.
    """
    from ...futures import Promise
    from ...tickdispatcher import TickDispatcher

    prom = Promise()
    cids = list(consoles_of(to, consoles))
    if not cids:
        # Resolve with the position rather than None: Promise.done() tests
        # `_result is not None`, so a None result is indistinguishable from never
        # having resolved - and a story awaiting it would hang forever.
        prom.set_result(lens_at(0.0))
        return prom

    camera_move_stop(cids)
    start = _now()
    seconds = max(0.0001, float(seconds))
    # A generation token, so a driver that outlives its stop cannot keep aiming.
    # The dispatcher holds tasks in a SET, so two drivers on one console would
    # otherwise fight in whatever order iteration happens to give - the last to
    # run winning each frame, which reads as a camera tearing between two paths.
    token = object()

    def _owns():
        for cid in cids:
            state = _MOVES.get(cid)
            if state is not None and state.get("token") is token:
                return True
        return False

    def _tick(t):
        if not _owns():
            t.stop()
            return
        #
        # SUBJECT GONE. Engine-observed: a dolly that is deleted mid-shot does not
        # freeze the frame - the view falls to the engine's own default (a top-down
        # on a station). So there is nothing to be gained by continuing to aim at a
        # dead id, and a driver that did would hold the story on a garbage frame.
        #
        # Stop and RESOLVE instead: a cutscene written as `await camera_move(...)`
        # then advances to its next shot, which is exactly the right recovery and
        # costs the author nothing. The library will not pick a new shot itself -
        # that is a directing decision it cannot make.
        #
        from ..query import to_object
        if to_object(subject) is None:
            t.stop()
            camera_move_stop(cids)
            if not prom.done():
                prom.set_result(_MOVES.get(cids[0], {}).get("lens") or lens_at(0.0))
            return
        elapsed = _now() - start
        raw = elapsed / seconds
        if raw > 1.0:
            raw = 1.0
        where = lens_at(_ease(ease, raw))
        camera_shot(cids, subject, where)
        for cid in cids:
            state = _MOVES.get(cid)
            if state is not None:
                state["lens"] = where
        if raw >= 1.0:
            t.stop()
            camera_move_stop(cids)
            if not prom.done():
                prom.set_result(where)

    # Every tick: the driver IS the animation, so a coarser interval is visible as
    # a stutter rather than a saving.
    task = TickDispatcher.do_interval(_tick, 0)
    for cid in cids:
        _MOVES[cid] = {"task": task, "lens": lens_at(0.0), "subject": subject,
                       "token": token}
    # AIM NOW, not on the first tick. Waiting a frame leaves the lens wherever the
    # last shot put it for one frame - a visible pop at the top of every move, and
    # the reason a cut into a move looked like a cut into the OLD shot.
    where0 = lens_at(0.0)
    camera_shot(cids, subject, where0)
    return prom


def camera_move(to, subject, lens_from, lens_to, seconds, ease="in_out",
                consoles=None):
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
        await camera_move(role("mainscreen"), hero, Vec3(0,900,-4000), Vec3(0,300,-900), 6)
    """
    a = _vec(lens_from) or Vec3(0, 0, 0)
    b = _vec(lens_to) or Vec3(0, 0, 0)

    def _at(u):
        return Vec3(a.x + (b.x - a.x) * u,
                    a.y + (b.y - a.y) * u,
                    a.z + (b.z - a.z) * u)

    return _drive(to, consoles, subject, seconds, _at, ease)


def camera_dolly(to, subject, from_distance, to_distance, yaw=0.0, pitch=12.0,
                 seconds=20.0, ease="in_out", consoles=None):
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
        Promise: resolves when the push ends.
    """
    from ..query import to_object
    a = float(from_distance)
    b = float(to_distance)

    def _at(u):
        # RESOLVED PER TICK, like camera_chase. Not because a held agent reports a stale
        # POSITION - `pos` proxies through to the live engine object, so it does not.
        # Because a subject that is not resolvable at ISSUE time pins `subj` to None for
        # the life of the move, framing every tick around the world ORIGIN with no
        # recovery; and the subject-died path can read an engine object already freed.
        # Cutscene subjects are resolved late, so this is a live case, not a corner.
        subj = to_object(subject)
        offset = camera_orbit_lens(a + (b - a) * u, yaw, pitch)
        base = subj.pos if subj is not None else Vec3(0, 0, 0)
        return Vec3(base.x + offset.x, base.y + offset.y, base.z + offset.z)

    return _drive(to, consoles, subject, seconds, _at, ease)


def camera_orbit(to, subject, distance, from_yaw=0.0, to_yaw=360.0, seconds=10.0,
                 pitch=15.0, ease="linear", consoles=None):
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
        Promise: resolves when the sweep ends.
    """
    from ..query import to_object

    def _at(u):
        # Per tick, for the reason camera_dolly gives: resolved once, a subject that is
        # not resolvable at issue time orbits the world origin for the whole sweep.
        subj = to_object(subject)
        yaw = from_yaw + (to_yaw - from_yaw) * u
        offset = camera_orbit_lens(distance, yaw, pitch)
        base = subj.pos if subj is not None else Vec3(0, 0, 0)
        return Vec3(base.x + offset.x, base.y + offset.y, base.z + offset.z)

    return _drive(to, consoles, subject, seconds, _at, ease)


def camera_chase(to, subject, distance, height=0.0, seconds=30.0, consoles=None):
    """Third person: hold the lens BEHIND the subject as it turns.

    The one move whose lens is a function of the subject's HEADING rather than of time, so it
    ignores the eased progress and reads the world each tick. That is the whole trick, and it
    is only possible because `_drive` calls `lens_at` per tick rather than sampling a path up
    front.

    WHY THIS IS NOT A TRACTOR. The intuitive way to chase is to attach the camera to the
    target and let the engine drag it. There is nothing to attach: the dolly and the target
    must be the SAME object or the frame is black, so the lens already rides the subject - a
    tractored camera object would be dragged along with nothing looking through it. Following
    IS re-aiming, and the engine has no interpolation to do it for us.

    WHY IT MUST RUN ON THE TICK. Re-aiming from a mission loop at a few hertz reads as a
    stutter, not as a saving - the same note `_drive` carries. A chase driven from a 0.5s
    mission tick flickers; the same maths on the dispatcher does not.

    A world-space offset does NOT rotate with the dolly, which is why the offset is rebuilt
    from `forward_vector()` every tick instead of being computed once. A subject with no usable
    heading (a rock, or an engine object that will not answer) falls back to a fixed offset
    rather than raising - a chase that is merely not behind the ship still shows the ship.

    Args:
        distance (float): how far BEHIND the subject to sit.
        height (float): how far above it. A little is usually better than none.
        seconds (float): how long this leg runs. Re-issue it to keep chasing - the same way
            an orbit is re-issued lap by lap.

    Returns:
        Promise: resolves when the leg ends, or when the subject goes.
    """
    from ..query import to_object

    def _at(_u):
        subj = to_object(subject)
        if subj is None:
            return Vec3(0, 0, 0)
        base = subj.pos
        try:
            fwd = subj.engine_object.forward_vector()
            fx, fy, fz = fwd.x, fwd.y, fwd.z
            flen = math.sqrt(fx * fx + fy * fy + fz * fz)
        except Exception:
            flen = 0.0
        # _engine_lens: this computes a real world position from the subject's HEADING,
        # so it is one of the shots the engine's mirrored offset actually breaks. Handed
        # over straight, "behind" rendered in FRONT of the thing being chased - the one
        # thing the docstring above promises not to do.
        if flen <= 1e-6:
            return _engine_lens(base, Vec3(base.x, base.y + height, base.z - distance))
        fx, fy, fz = fx / flen, fy / flen, fz / flen
        return _engine_lens(base, Vec3(base.x - fx * distance,
                                       base.y + height - fy * distance,
                                       base.z - fz * distance))

    return _drive(to, consoles, subject, seconds, _at, "linear")


def camera_rack(to, subject, consoles=None):
    """Look at something else WITHOUT moving the lens - a rack focus.

    Holds the current world position and re-aims at ``subject``. Any running move is
    stopped first: a rack during a move is a new intent, not a modifier on the old one.

    Returns:
        int: how many consoles were re-aimed.
    """
    lens = camera_lens(to, consoles)
    camera_move_stop(to, consoles)
    if lens is None:
        # Nothing recorded (no move has run) - the caller has to say where the lens
        # is, because the engine cannot be asked.
        return 0
    n = camera_shot(to, subject, lens, consoles=consoles)
    for cid in consoles_of(to, consoles):
        _MOVES[cid] = {"task": None, "lens": lens, "subject": subject,
                       "token": None}
    return n


# --- The establishing two-shot ----------------------------------------------
#
# The shot everyone pictures when they say "in orbit": the ship in frame with the
# world behind it, or beside it, or dropping away below. `camera_orbit` cannot make
# it - that swings the lens around ONE object, so pointing it at the planet gives a
# planet with no ship in it, and pointing it at the ship gives a ship against stars
# with the planet wherever it happens to fall.
#
# What makes this shot is that the lens is placed in the frame the TWO bodies define:
#
#   r  radial   - from the world out to the ship. Sit here and the world is BEHIND.
#   t  tangent  - along the ship's travel. Sit here and the world is to one SIDE.
#   u  up       - sit here and look down across the ship at the world below.
#
# Every angle below is a blend of those three, so it keeps working as the ship moves
# round its orbit: the frame is recomputed from live positions each tick, not fixed
# in world space.

# name -> (cone, roll). NOT a free blend of the three axes, and that distinction is the
# whole difference between a shot that works and one that merely runs.
#
# The lens always sits within a narrow CONE about the radial axis - the line from the
# world out through the ship - so the camera is always looking roughly world-ward and the
# body is always in the picture. `cone` is how far off that axis to lean, in degrees;
# `roll` is which way to lean, around the axis. Roll is what changes the COMPOSITION -
# world behind, off one edge, below, above - while the cone keeps it on screen.
#
# A free blend does not do this. A tangent-dominant offset puts the lens abeam the ship,
# and from there the world is ~70 degrees off the view axis: still "in frame" if you only
# ask whether its limb clips the corner, and not on screen at all in any real field of
# view. That is exactly what shipped first, and what the reference stills are not.
# Retuned once the camera moved onto its OWN wider orbit. The cone is how far around
# the world the lens sits from the ship's own bearing - it is NOT the on-screen gap.
# Sitting further out multiplies it: at 1.45x the ship's radius a 34 degree cone opens
# a 42 degree gap between hull and world on screen, which is most of a frame.
ESTABLISHING_ANGLES = {
    "behind": (14.0, 25.0),    # world filling the frame behind the ship
    "side":   (34.0, 0.0),     # world crowded into one edge
    "high":   (30.0, 95.0),    # looking down across the hull, world below
    "low":    (28.0, 255.0),   # up past the hull, world above it
}
# How far off the world-ward axis any angle may lean. A composition wider than this puts
# the body off screen on a normal lens, whatever its size.
ESTABLISHING_MAX_CONE = 40.0
def _engine_lens(base, want):
    """The offset to HAND the engine so the lens ends up at ``want``.

    THE ENGINE PUTS THE LENS ON THE FAR SIDE OF THE OFFSET IT IS GIVEN - mirrored
    through the dolly. Engine-observed 2026-08-31 on an orbital establishing shot, with
    the geometry logged and correct: the shot came out on the world side of the ship
    looking away from it, and the orbit tether ran from the hull toward the camera,
    which it can only do if the camera is between ship and world.

    It hid for as long as it did because it is INVISIBLE to a single-subject shot: a
    lens mirrored through its subject still frames that subject, just from a side
    nobody asked for. `camera_orbit_lens` even documents ``Vec3(0, 0, distance)`` as
    "straight back", which is only true once mirrored - the offsets in this module were
    authored against the behavior, not against the arithmetic.

    So the shots that are WRONG are the ones that compute a real world position from
    real geometry - a chase that must be behind a heading, an establishing shot that
    must be opposite a world. Those go through here. The angle-based shots
    (`camera_dolly`, `camera_orbit`) build their offset in the engine's own convention
    and are left exactly as they are.
    """
    return Vec3(2.0 * base.x - want.x, 2.0 * base.y - want.y, 2.0 * base.z - want.z)

def camera_establishing(to, subject, world, angle="behind", distance=None,
                        seconds=14.0, arc=8.0, consoles=None):
    """Frame ``subject`` AND ``world`` together - the orbital establishing shot.

    Both bodies in one picture: the ship close enough to read, the world filling the
    space behind it or crowding one edge. `camera_orbit` cannot make this - it swings
    around ONE object, so pointed at the world there is no ship in shot, and pointed at
    the ship the world falls wherever the heading puts it.

    The lens is placed within a narrow cone about the WORLD-WARD axis (the line from the
    world out through the ship), so the camera always looks roughly world-ward and the
    body cannot leave the picture. ``angle`` names how far off that axis to lean and
    which way, and the frame is rebuilt from live positions each tick, so the
    composition holds all the way round the orbit.

    Args:
        to: audience (see ``consoles_of``).
        subject: what is framed and tracked - the SHIP.
        world: the body it is in orbit of. Only its position is used, so a planet, a
            station or a marker all work. ``None`` degrades to a plain tracking shot.
        angle (str): a key of ``ESTABLISHING_ANGLES``, or a ``(cone, roll)`` pair in
            degrees. Cone is clamped to ``ESTABLISHING_MAX_CONE``.
        distance (float, optional): lens distance from the subject. Defaults to a
            framing scaled off the subject's own size.
        seconds (float): length of the leg.
        arc (float): degrees of slow roll across the leg, so the shot breathes rather
            than sitting dead still. 0 holds it fixed.

    Returns:
        Promise: resolves when the leg ends.

    Example:
        await camera_establishing(role("mainscreen"), ship, planet, angle="side")
    """
    from ..query import to_object

    pair = ESTABLISHING_ANGLES.get(angle, angle) if isinstance(angle, str) else angle
    try:
        cone, roll = float(pair[0]), float(pair[1])
    except Exception:
        cone, roll = ESTABLISHING_ANGLES["behind"]
    cone = max(0.0, min(float(ESTABLISHING_MAX_CONE), cone))

    if distance is None:
        # Scaled off the SHIP. Putting the camera on its own wider orbit round the
        # world was tried and is worse: the hull shrinks to a speck and the angles
        # stop reading as angles.
        from .viewscreen import viewscreen_framing
        near, far = viewscreen_framing(subject)
        distance = (near + far) * 0.5
    distance = float(distance)

    def _at(u):
        # Resolved per tick for the same reason camera_dolly does it: a subject that is
        # not resolvable at ISSUE time would pin the frame to the world origin for the
        # life of the move, with no recovery.
        subj = to_object(subject)
        body = to_object(world)
        if subj is None:
            return Vec3(0, 0, 0)
        base = subj.pos
        if body is None:
            # Nothing to play the ship against - degrade to a plain back-and-above
            # angle rather than framing the world origin.
            from .viewscreen import viewscreen_framing
            _near, _far = viewscreen_framing(subject)
            off = camera_orbit_lens((_near + _far) * 0.5, yaw=0.0, pitch=12.0)
            return Vec3(base.x + off.x, base.y + off.y, base.z + off.z)

        # The world-ward axis: from the body out through the ship. Sit ON it and the
        # world is dead behind the ship; every angle is a small lean off it.
        radial = Vec3(base.x - body.pos.x, base.y - body.pos.y, base.z - body.pos.z)
        rl = radial.length()
        if rl < 0.001:
            radial = Vec3(0, 0, 1)
            rl = 1.0
        radial = Vec3(radial.x / rl, radial.y / rl, radial.z / rl)

        side = Vec3(0, 1, 0).cross(radial)
        sl = side.length()
        if sl < 0.001:
            # Directly over a pole: "along the orbit" is undefined and the cross product
            # collapses, so any perpendicular will do.
            side = Vec3(1, 0, 0)
            sl = 1.0
        side = Vec3(side.x / sl, side.y / sl, side.z / sl)
        upish = radial.cross(side)

        theta = math.radians(cone)
        phi = math.radians(roll + (u - 0.5) * float(arc))
        ct, st = math.cos(theta), math.sin(theta)
        cp, sp = math.cos(phi), math.sin(phi)
        dx = radial.x * ct + (side.x * cp + upish.x * sp) * st
        dy = radial.y * ct + (side.y * cp + upish.y * sp) * st
        dz = radial.z * ct + (side.z * cp + upish.z * sp) * st

        # Where the lens should BE: out past the ship along the world-ward axis, so the
        # shot looks back down that axis at the hull with the world behind it.
        want_x = base.x + dx * distance
        want_y = base.y + dy * distance
        want_z = base.z + dz * distance
        return _engine_lens(base, Vec3(want_x, want_y, want_z))

    return _drive(to, consoles, subject, seconds, _at, "in_out")
