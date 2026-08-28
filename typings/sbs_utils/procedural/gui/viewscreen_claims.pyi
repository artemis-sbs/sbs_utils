def DEBUG (msg):
    ...
def _baseline_capture (ship_id, baseline, cids):
    """Record the crew's state, once, on the way from unclaimed to claimed.
    
    The sentinel is the BASELINE being unset, not ``viewscreen_is_live``. A story
    claim never sets a viewer mode, so asking whether a shot is running would let a
    second capture through - and a second capture overwrites the crew's own state
    with whatever the first claimant had put up."""
def _baseline_drop (ship_id):
    ...
def get_counter_elapsed_seconds (id_or_obj, name, default_value=None):
    """Return the number of seconds elapsed since a counter was started.
    
    Args:
        id_or_obj (Agent | int): Agent ID or object.
        name (str): Counter name.
        default_value (optional): Value returned if the counter was never
            started. Defaults to None.
    
    Returns:
        float | None: Seconds elapsed, or ``default_value`` if not set.
    
    Example:
        elapsed = get_counter_elapsed_seconds(SHIP_ID, "docked", 0)
        if elapsed > 60:
            "Docking complete.""""
def get_inventory_value (id_or_object, key: str, default=None):
    """Get an inventory value from an agent by key.
    
    Args:
        id_or_object (Agent | int): The agent ID or object.
        key (str): The inventory key.
        default (any, optional): Value returned when the key is absent.
            Defaults to None.
    
    Returns:
        any: The inventory value, or ``default`` if the key is not set."""
def set_inventory_value (so, key: str, value):
    """Set an inventory value on one or more agents.
    
    If ``so`` is a set or collection, every member receives the value.
    
    Args:
        so (Agent | int | set[Agent | int]): The agent(s) to update.
        key (str): The inventory key.
        value (any): The value to store."""
def start_counter (id_or_obj, name):
    """Record the current sim tick as the start of a named counter.
    
    Use ``get_counter_elapsed_seconds`` to read how many seconds have passed
    since the counter was started. Use ``set_interval`` for a counter that emits
    a signal every so often instead of being read.
    
    Restarting a counter that ``set_interval`` armed restarts its beat too - the
    next one lands a full interval from now.
    
    Args:
        id_or_obj (Agent | int): Agent ID or object.
        name (str): Counter name.
    
    Example:
        start_counter(SHIP_ID, "docked")
        # later...
        secs = get_counter_elapsed_seconds(SHIP_ID, "docked")"""
def to_id (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """Extract the integer ID from an agent, ``CloseData``, ``SpawnData``, or bare int.
    
    Args:
        other (Agent | CloseData | SpawnData | int): Value to convert.
    
    Returns:
        int: The integer agent ID."""
def viewscreen_baseline (ship):
    """The ``(view, facing, mode)`` the crew had before anyone took the screen."""
def viewscreen_baseline_drop (ship):
    """Forget the baseline without restoring it.
    
    What a helm takeover does: helm's choice IS the new state, so there is nothing
    to go back to and leaving a stale baseline recorded would let a later,
    unrelated release put the crew's screen somewhere they left minutes ago."""
def viewscreen_bump (ship):
    """Advance the sequence. Call BEFORE the outcome, never after."""
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
def viewscreen_held (ship):
    """The crew request parked behind a story claim, or None."""
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
def viewscreen_owner (ship):
    """Who holds this ship's main screen, or ``""``."""
def viewscreen_owner_token (kind, client_id=None):
    """The owner token for a claimant.
    
    Per-CONSOLE for anything a crew member drives (``science``, ``weapons``), bare
    for anything the ship has one of (``hail``, ``docking``). Two science consoles
    on one bridge are two different claimants; one bridge has only one docking."""
def viewscreen_owns (ship, owner):
    """Is ``owner``'s claim still the live one?
    
    The question a console should ask before acting on the screen it thinks it is
    driving. LegendaryMissions' weapons console hand-rolled this as a private
    ``WEAP_VIEWER_SUBJECT`` inventory value, and science never asked at all - which
    is why science re-pointing on a new selection used to yank a shot weapons had
    set up."""
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
def viewscreen_tier (ship):
    """``"console"``, ``"story"``, or ``""`` when nothing holds the screen."""
