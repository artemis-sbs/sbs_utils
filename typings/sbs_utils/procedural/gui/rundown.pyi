def _apply (cids, shot, clear_slots):
    ...
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
def consoles_of (to, consoles=None):
    """Resolve an audience expression to a set of console client ids.
    
    Args:
        to: ``None`` (the current console), a client id, a ship id/object, a side
            key or side agent, or a set/list mixing any of those.
        consoles (str, optional): narrow to consoles with these roles, e.g.
            ``"mainscreen"`` or ``"science, comms"``.
    
    Returns:
        set[int]: console client ids (possibly empty)."""
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
def rundown_add (name, subject, lens=None, move=None, seconds=4, ease='in_out', label=None, overlay=None, framing=None, yaw=None, pitch=None):
    """Add (or replace) a shot in the rundown.
    
    Args:
        name (str): how the director refers to it.
        subject: what the shot looks at - and necessarily what the lens rides.
        framing: a named size (``close``/``medium``/``wide``), or two for a move.
            PREFERRED over lens/move - the distance is taken from the subject own
            hull, so one shot frames a runabout and a starbase alike.
        lens: world position for a static shot.
        move: ``[from, to]`` world positions for a moving one.
        seconds (float): duration of a ``move`` (a static shot holds until punched away).
        label (str, optional): what the director's tile says. Defaults to ``name``.
        overlay (dict, optional): furniture to show with it, ``{"kind": ..., ...}``.
    
    Returns:
        dict: the stored shot."""
def rundown_clear ():
    """Empty the rundown and both desks."""
def rundown_excitement (name):
    """How interesting this shot's subject is right now.
    
    Reads the engine's own ``exciting`` value - the same notion its automatic
    cinematic camera follows - so a suggestion agrees with what the engine would
    have picked, rather than being a second opinion invented here."""
def rundown_get (name):
    ...
def rundown_live ():
    """The name of the shot on PROGRAM, or None. This is the tally."""
def rundown_preview (to=None, consoles=None):
    """Set (or read) the PREVIEW audience - the director's own console."""
def rundown_program (to=None, consoles=None):
    """Set (or read) the PROGRAM audience - the feed everyone sees.
    
    Naming the audience is also where each console's own ship is recorded, so the
    desk can give it back at release. Captured HERE rather than at the first punch
    because by then a shot has already reassigned somebody."""
def rundown_punch (name, flash=False):
    """Put a shot on PROGRAM. Returns True if it went live.
    
    A cut, because the engine only cuts. ``flash`` fakes a transition with a
    one-frame flash overlay - the only "effect" available, and it is honest about
    being a fake rather than pretending to dissolve."""
def rundown_release ():
    """Hand PROGRAM back to the engine's own director and clear the tally.
    
    The end-of-show path - and the one to call BEFORE deleting anything a shot was
    riding, since a deleted dolly drops the view to the engine default."""
def rundown_remove (name):
    """Drop a shot. If it was live, the tally is cleared - the feed does not change,
    because pulling a shot out of a list is not a directing decision."""
def rundown_shots ():
    """Every shot, in rundown order."""
def rundown_stage (name):
    """Line a shot up on PREVIEW without touching PROGRAM. Returns True if staged."""
def rundown_staged ():
    """The name of the shot on PREVIEW, or None."""
def rundown_suggest (exclude_live=True):
    """The shot worth punching to, or None. **Assist, never autopilot.**
    
    Args:
        exclude_live (bool): skip whatever is already live, since suggesting the
            shot the director is already on is noise."""
def rundown_take (flash=False):
    """Punch what is on PREVIEW. The broadcast take. Returns the name, or None."""
def rundown_tiles ():
    """Everything a director's console needs to draw the rundown.
    
    A list of ``{name, label, live, staged, suggested, excitement}`` in rundown
    order. Returned as DATA so the console is a mission's to design - this layer
    has no opinion about what a tile looks like."""
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
