from sbs_utils.helpers import FrameContext
def camera_auto (to=None, consoles=None):
    """Hand the camera back to the engine's own director (it follows the assigned ship).
    
    The release path for anything `camera_track` took over - end a cutscene with this.
    
    Args:
        to: audience (see ``consoles_of``); ``None`` is the current console.
        consoles (str, optional): narrow to consoles carrying these roles.
    
    Returns:
        int: how many consoles were released."""
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
def camera_shot (to, subject, lens_world, consoles=None):
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
            the lens rides; ``lens`` (world position) OR ``move`` ([from, to]);
            ``seconds`` (default 4); ``ease``; ``overlay`` ({"kind": ..., plus that
            kind's fields}).
        letterbox (bool): black bars for the duration.
        skippable (bool): whether ``cutscene_skip`` ends it.
        bar (float): letterbox bar height in em.
        release (bool): hand the camera back to the engine's director at the end.
            Leave it True unless the next thing the story does is set its own shot -
            a cutscene that ends still holding a dolly will drop to the engine
            default the moment that object is deleted.
    
    Returns:
        dict: the stored cutscene."""
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
    """Clear one slot (or all slots if ``slot`` is None) on the ``to`` targets."""
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
    caller can clear exactly what it put up."""
def shot_furniture (cids, shot):
    """Show a shot's overlay, if it has one. Returns the slots it used."""
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
