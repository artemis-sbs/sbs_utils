from sbs_utils.helpers import FrameContext
from sbs_utils.tickdispatcher import TickDispatcher
def _advance_reel (src, tgt, st):
    ...
def _attach_allowed (src, tgt):
    ...
def _delete_connection (src, tgt):
    """Drop the ENGINE connection for a registry pair, whichever way round it was built.
    
    A mass-reversed tether was created as (target, source), so deleting only the pair the
    caller knows about would leave the real connection live and the load still held."""
def _distance (a_obj, b_obj):
    ...
def _drag_amount (ratio):
    """How much drive a load of this mass ratio costs. 0 = free, 0.75 = at the floor."""
def _drag_recheck (src):
    """Lift the tow drag, and re-arm any tether this ship still holds.
    
    A ship towing two things that lets one go should end up dragged by what is LEFT, not
    by what it dropped and not by nothing. Clearing the cached amount makes the next tick
    recompute from whatever remains."""
def _enforce_drag (src, tgt, st):
    """Towed mass drops the puller's throttle and turn rate.
    
    This is what makes big salvage a slow, vulnerable trip home rather than free money.
    Applied as MODIFIERS on the engine's own upgrade coefficients (the same keys the item
    system boosts), so it stacks and expires through machinery that already exists instead
    of fighting the helm for the throttle value every tick.
    
    A SWING is exempt: the anchor is the source, the fighter is the load, and slowing the
    anchor (usually a rock) means nothing - while slowing the fighter would kill the orbit
    the mode exists for."""
def _enforce_impulse (src, tgt, st):
    """Impulse-only rule. Returns True if the tether was snapped (removed)."""
def _ensure_tick ():
    ...
def _maybe_stop_tick ():
    ...
def _release_drag (src):
    """Lift the tow drag. Called on release - a ship that let go must get its drive back."""
def _sbs ():
    ...
def _sim ():
    ...
def _spend_tow_energy (src, tgt, st):
    """Charge the puller for holding a load. Returns True if the tether snapped dry.
    
    Running a ship's reserves to nothing would be a worse mechanic than making the haul
    expensive, so an empty tank BREAKS the beam and drops the load rather than pinning the
    ship at zero energy."""
def _tick_rope (src, tgt, st):
    """Rope-toggle: taut (beyond rope_len) -> engage a stiff pull back to the circle;
    slack (inside) -> release the pull so the target moves free. Holds a load/ship at
    rope_len (a static tether would reel it fully in)."""
def _tick_swing (anchor, ship, st):
    """Circle-point orbit: aim the pull at the point on the rope_len circle at the ship's
    CURRENT bearing (in the XZ plane). That correction is radial-only, so it holds the
    radius while the ship's own throttle carries it around — no spiral-in, no killed
    tangential motion. Re-points every tick since the connection's offset isn't settable."""
def _to_sbs_vec (offset):
    """Accept None / an sbs.vec3 / a sbs_utils Vec3 / an (x,y,z) tuple."""
def get_data_set_value (id_or_obj, key, index=0):
    """Get a value from the engine data-set (blob) of a space or grid object.
    
    Args:
        id_or_obj (Agent | int): The agent ID or object.
        key (str): The data-set key.
        index (int, optional): The slot index within that key. Defaults to 0.
    
    Returns:
        any: The stored value, or ``None`` if the object or key is not found."""
def grav_tether_attach (source, target, offset=None, stiffness=0.0, pull_distance=0.0, overspeed=None):
    """Open (or replace) a tether so ``source`` pulls ``target``.
    
    offset        - point (relative to source) the target is pulled toward.
    stiffness     - the connection's .offset dial: 0 = rigid lock, ~5 = taut tow.
    pull_distance - rope rest-length; the target settles at this distance.
    overspeed     - per-tether enforcement mode; None uses the module default.
    Returns the tractor_connection, or None if either object is missing."""
def grav_tether_clear_all ():
    """Drop all tethers (fresh mission / test reset).
    
    Drops OUR tethers one by one rather than calling ClearTractorConnections(), which is
    global: the engine has a single tractor pool, and other systems build connections in
    it that are not tethers. `procedural.mount` welds a turret to a hull with one, and a
    global clear silently unwelded every mount while mount's own bookkeeping went on
    insisting they were attached. Deleting only what this module registered keeps the two
    uses independent.
    
    Tolerates having no sim: this runs from reset_mission_state(), which can fire with no
    frame context at all, and dropping our own state must never depend on the engine
    being there. The engine-side connections die with the old sim regardless."""
def grav_tether_get (source, target):
    """Return the live tractor_connection for the pair, or None."""
def grav_tether_has (source, target):
    """True if this exact PAIR is tethered — ask this, not :func:`grav_tether_get`.
    
    `grav_tether_get` returns the live ENGINE connection, and a Tow is a rope-TOGGLE: it
    deletes the connection whenever the load is inside the rope length and re-adds it when
    the load drifts out. So `get` reads None for most of a perfectly good tow, and a UI
    gated on it offers "Tow" to something already under tow and never offers "Release".
    
    Use `get` only when you want the engine object itself (to read `.offset`)."""
def grav_tether_involves (obj):
    """True if obj is either end (source or target) of any live tether — for a one-button
    toggle where the ship may be the puller (tow/reel) or the pulled (swing).
    
    Registry-based, so it is honest during a rope-toggle tow (see :func:`grav_tether_has`)."""
def grav_tether_lock (source, target, offset=None, overspeed=None):
    """Rigid grab: target locked onto the source's offset point (cargo, hangar recovery)."""
def grav_tether_mass (obj):
    """What this object weighs, via the installed provider. Never returns 0."""
def grav_tether_mass_ratio (source, target):
    """target mass / source mass. >1 means the LOAD is the heavier end.
    
    The one number the constraints layer turns on: who drags whom, and how much it costs
    the puller."""
def grav_tether_reel (source, target, rate=50.0, stiffness=5.0, offset=None, overspeed=None):
    """Reel the load in: start the rope at the current separation and ramp it to 0,
    then emit ``grav_tether_reeled`` for the caller to hand off (collect / dock)."""
def grav_tether_release (source, target):
    """Break a single tether (source no longer pulls target). Safe if none exists."""
def grav_tether_release_all (source):
    """Break every tether where ``source`` is the puller."""
def grav_tether_is_anchor (obj):
    """Whether this object can only ever be the anchor end of a tether."""
def grav_tether_release_any (obj):
    """Release every tether obj is part of, at either end."""
def grav_tether_rope (source, target, rope_len, stiffness=5.0, overspeed=None):
    """Hold the target at ~``rope_len`` from the source via a per-tick ROPE-TOGGLE:
    beyond rope_len a stiff pull snaps it back to the circle; inside, the tether is
    released so it moves free. Engine-confirmed (data harness): a STATIC tether reels
    the target fully in regardless of pull_distance (1500 -> ~165), so holding a load
    *at* a distance REQUIRES this toggle (which held 798/801/801 at rope_len=800). Both
    Tow (source drags a trailing load) and Swing (anchor holds the ship) are this same
    rope-hold — only the source/target roles differ."""
def grav_tether_set_anchor_roles (roles):
    """Set the roles that may never be PULLED (comma-separated, or "" to allow all).

    A mission that wants the library default back passes :data:`ANCHOR_ROLES`."""
def grav_tether_set_attach_policy (fn):
    """Install (or clear with None) the attach veto callback. An attach whose
    fn(source_id, target_id) returns False is refused (attach returns None)."""
def grav_tether_set_grab_speed_limit (limit):
    """Refuse a grab on anything moving faster than `limit` throttle. None = no rule."""
def grav_tether_set_mass_fn (fn):
    """Install (or clear with None) the mass provider: fn(id) -> float.
    
    Without one every object weighs :data:`DEFAULT_MASS`, so the mass rules below all
    reduce to "evenly matched" - no gating, no drag. That is deliberate: a library that
    guessed at mass would be confidently wrong, and a mission that has not said what
    things weigh should get the un-gated behavior it had before."""
def grav_tether_set_overspeed_default (mode):
    """Set the module default overspeed mode (cap / snap / off) for new tethers."""
def grav_tether_set_tow_energy_cost (per_mass_per_tick):
    """Energy the puller spends per tick, per unit of towed mass. 0 = free."""
def grav_tether_sources_of (target):
    """List the source ids currently tethering ``target`` (a tow/lock source, or a swing
    anchor). Lets a mission see who is working a shared quest target (claim-on-tether)."""
def grav_tether_swing (anchor, ship, rope_len, stiffness=1.0, overspeed=None):
    """Fighter swing (SECONDARY): hold the ship on a CIRCLE of radius rope_len around the
    anchor so it orbits on its own throttle. A plain rope-toggle pulls toward the anchor
    *center*, which has no centrifugal balance and spirals the ship in (measured 758→663).
    Instead each tick we aim the pull at the point on the circle at the ship's CURRENT
    bearing — a purely radial correction that holds the radius without killing tangential
    motion. Engine-confirmed a player hull can be tractor-pulled; final feel is a fly-it."""
def grav_tether_target_too_fast (target):
    """Whether this target is moving too fast to get hold of."""
def grav_tether_tick (t=None):
    """Runs on the TickDispatcher (~10 Hz) while any tether is live; also directly
    callable (tests). Enforces impulse and advances reels; self-heals dead objects."""
def grav_tether_tow (source, target, distance, stiffness=5.0, overspeed=None):
    """Trailing tow: hold the load at ~``distance`` from the source via the rope-toggle
    (a static tether would reel it fully in). As the source moves, the load trails behind
    at that distance - no offset needed here; the drag makes it trail for free.
    
    NOTE the offset point is only "world-fixed" in the sense that THIS module never
    passes one. Engine-measured (LM_TestRange/maps/test_tractor_mount.mast):
    ``AddTractorConnection(host, target, vec3(0,0,200), 0)`` holds the target in the
    SOURCE'S BODY FRAME - exactly 200u at exactly 0 deg off the nose while the host's
    heading swung 51 deg. Passing no offset is what makes a load reel to the source's own
    position, which is what a tow wants and what the "reels fully in regardless of
    pull_distance" measurement was really showing. To bolt something ON to a hull rather
    than drag it behind one, use :mod:`sbs_utils.procedural.mount`."""
def object_exists (so_id):
    """Return whether an object currently exists in the simulation.
    
    Args:
        so_id (Agent | int): Agent ID or object.
    
    Returns:
        bool: ``True`` if the engine reports the object present."""
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
