from sbs_utils.helpers import FrameContext
from sbs_utils.tickdispatcher import TickDispatcher
def _add_connection (src, tgt, offset, pull):
    """Create the ENGINE connection for a registry pair. May return None: the engine can
    refuse one (a static body is the likely case), and dereferencing that None inside the
    tick is how a single tether used to pause the whole sim."""
def _advance_reel (src, tgt, st):
    ...
def _announce_strain (src, tgt, st):
    """Emit ``grav_tether_strain`` when this haul crosses into a new strain band.
    
    EDGE-TRIGGERED, because this runs on the tether tick several times a sim-second and a
    signal at that rate is a flood, not feedback. The edge is (band, crew size), so a tug
    arriving is announced even when it does not move the band - which it usually will not,
    since a four-ship team spans about one band and the CREW COUNT is the legible half of
    the news. Neither input is noisy: masses are constant and the puller set changes only
    when somebody attaches or lets go, so there is nothing here to chatter on and no need
    for a dead band.
    
    FAN-OUT: when a fourth tug joins, all four tethers see a changed crew and all four
    emit. That is one signal per SHIP, which is what a per-console readout wants - but a
    handler that broadcasts must address SOURCE_ID, or one ship joining prints four
    identical lines into the same waterfall.
    
    The reason it exists at all is that every cost this module charges was invisible. A
    crew hauling a starbase was capped to impulse, cut to a quarter throttle and burning
    its reserves, and nothing anywhere said so - the ship simply felt broken. Two signals
    existed and both fired only after the haul had already failed."""
def _attach_allowed (src, tgt):
    ...
def _attach_guard (src, tgt):
    """Every refusal rule, in one place. True when the tether may be created.
    
    `tgt` is always the end of the rope - the load for a lock/tow/reel, and the SHIP for
    a swing, where the anchor is the source. That is what lets one rule cover both: a
    black hole may anchor a slingshot and may never be dragged."""
def _conn_pair (src, tgt):
    """The ENGINE pair for a registry key, whichever way round the mass rule built it.
    
    A mass-reversed tether was created as (target, source), so touching only the pair the
    caller knows about leaves the real connection live and the load still held. EVERY
    engine call for a registered tether goes through here - the reel ramp and the rope
    toggle used to re-add the raw (src, tgt) each tick, which on a reversed tether left
    the reversed connection pulling AND built a second one facing the other way."""
def _delete_connection (src, tgt):
    """Drop the ENGINE connection for a registry pair, whichever way round it was built."""
def _distance (a_obj, b_obj):
    ...
def _drag_amount (ratio):
    """How much drive a load of this mass ratio costs. 0 = free, 0.75 = at the floor."""
def _drag_floor_ratio ():
    """The ratio at which drag stops growing because it has hit :data:`DRAG_FLOOR`."""
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
    the mode exists for.
    
    A MASS-REVERSED tether is exempt too, and for the same reason read the other way up:
    drag is what HAULING costs, and on a reversed tether the caller is not hauling - they
    are the load, with the engine already moving their hull for them. Charging them as
    well stacked the two heaviest penalties this module has on the one ship that had
    earned neither: capped to impulse by _enforce_impulse AND cut to the DRAG_FLOOR (a
    starbase is 20-60x a cruiser, so the ratio pins the amount at its 0.75 ceiling), which
    is why grabbing something big read as "the engines stopped working".
    
    The ratio is the COMBINED one (:func:`grav_tether_load_ratio`): you are carrying a
    share of the load, not all of it, so a tug that joins the haul lightens it for
    everyone already pulling. That amount is recomputed from live state every tick and
    compared against the cached one, so a ship joining or leaving corrects every other
    puller on the next tick with no cache bookkeeping of its own."""
def _enforce_impulse (src, tgt, st):
    """Impulse-only rule. Returns True if the tether was snapped (removed)."""
def _ensure_tick ():
    ...
def _get_connection (src, tgt):
    """The live ENGINE connection for a registry pair, or None."""
def _hold_distance (st):
    """The distance this tether is entitled to hold across, or None when no rule applies."""
def _maybe_stop_tick ():
    ...
def _over_stretched (src, tgt, st):
    """Whether a live tether has been pulled past breaking."""
def _release_drag (src):
    """Lift the tow drag. Called on release - a ship that let go must get its drive back."""
def _sbs ():
    ...
def _sim ():
    ...
def _spend_tow_energy (src, tgt, st):
    """Charge the puller for its SHARE of holding a load. Returns True if it snapped dry.
    
    Running a ship's reserves to nothing would be a worse mechanic than making the haul
    expensive, so an empty tank BREAKS the beam and drops the load rather than pinning the
    ship at zero energy.
    
    THE SHARE IS WHAT MAKES A SECOND TUG WORTH CALLING. The load's bill is fixed by what
    it weighs; each puller pays it in proportion to its own mass. Charge every ship the
    FULL bill instead - which is what this did - and four hulls on one starbase each drain
    at the solo rate and all four cut out at the same moment: the fleet spends four times
    the power for not one extra second of haul. Shared, a lone tug pays exactly what it
    always did and four of them each last four times as long."""
def _tick_lock (src, tgt, st):
    """Harden a winching Grav Lock to rigid once the gap is actually closed.
    
    Measured against the LIVE separation, not against a ramped rope length: pull_distance
    is not honored as a rest length (the mock ignores it outright, and the engine harness
    read 1500 -> ~165 rather than -> 1500), so a countdown would be a timer pretending to
    be a measurement. Distance is the thing the rule is about, so distance is what it
    reads."""
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
def _tow_lag (src, tgt, st):
    """The beam's stiffness dial, scaled by how outmatched the ships on the load are.
    
    ``con.offset`` is a SPEED dial - engine-measured at ``offset x 30.2`` units per
    second, linear in offset and linear in time - so a heavy load divides it down and
    comes in slower. It was flat, so a 200-mass starbase came to the rope exactly as
    briskly as a 1-mass fighter: the tug felt the weight in drag and power and the LOAD
    felt nothing, which is why hauling a station read as free.
    
    Engine-measured pull speeds at the base stiffness of 5: 151 u/s evenly matched, about
    75 u/s on a freighter, and near 26 u/s for a lone cruiser on a science station - which
    four cruisers lift back to about 52.
    
    ONLY A TOW. Gated on the mode rather than on ``st["rope"]`` because grav_tether_rope
    is public and a mission may open a rope-hold that is not a tow. A swing's anchor is a
    rock (scaling would kill the orbit the mode exists for) and a lock on something heavy
    is REVERSED - the station is pulling you, which should be strong, not sluggish.
    
    Never faster than the nominal stiffness, and short-circuited entirely when no mission
    has said what anything weighs: an evenly matched tow, and every mission with no mass
    table, tows exactly as it always did."""
def get_data_set_value (id_or_obj, key, index=0, default=None):
    """Get a value from the engine data-set (blob) of a space or grid object.
    
    Args:
        id_or_obj (Agent | int): The agent ID or object.
        key (str): The data-set key.
        index (int, optional): The slot index within that key. Defaults to 0.
            **This is an INDEX, not a fallback** - the third positional argument is
            which slot to read (shield 0 vs shield 1), and passing a "default" there
            reads the wrong slot or fails outright.
        default (any, optional): what to return when the field has never been set.
            The engine answers ``None`` for such a field, and a mission that then
            compares it (``if fuel < 1000``) raises on a real bridge while running
            clean against the mock's typed defaults - the bug behind LM's Florbin
            cargo-hold watcher and an earlier helm crash. Pass ``default=0`` (or
            ``default=""``) and the caller gets something it can use. ``sbs lint``
            flags the unguarded shape as ``blob-unguarded-none``.
    
    Returns:
        any: The stored value, ``default`` if the object or key is not found."""
def grav_tether_attach (source, target, offset=None, stiffness=0.0, pull_distance=0.0, overspeed=None):
    """Open (or replace) a tether so ``source`` pulls ``target``.
    
    offset        - point (relative to source) the target is pulled toward.
    stiffness     - the connection's .offset dial: 0 = rigid lock, ~5 = taut tow.
    pull_distance - rope rest-length; the target settles at this distance.
    overspeed     - per-tether enforcement mode; None uses the module default.
    Returns the tractor_connection, or None if either object is missing."""
def grav_tether_between (a, b):
    """Whether these two are tethered to each other, whichever way round.
    
    `grav_tether_has` is directional, and a SWING is registered the other way up (the
    anchor is the source and the ship is the load). So a menu that asks `has(me, that)`
    is blind to a swing it opened itself: it goes on offering the grab and never offers
    Release, and the crew cannot let go. Ask this instead whenever the question is "is
    there a beam between these two", not "am I the puller"."""
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
def grav_tether_is_anchor (obj):
    """Whether this object can only ever be the anchor end of a tether."""
def grav_tether_load_ratio (source, target):
    """How outmatched the ships on ``target`` are, all of them together.
    
    The team-aware sibling of :func:`grav_tether_mass_ratio`, which stays a ONE-ship
    question on purpose: who gets reversed is about the ship that grabbed, while how hard
    the haul is is about every beam on the load. Every cost a tow pays comes from this,
    so a tug joining lightens the haul for everyone already on it.
    
    ``source`` is only the fallback: when nothing is registered as hauling the target -
    a caller asking before the tether exists, or from the reversed end - it stands in for
    the crew, so the answer is the plain one-ship ratio rather than a wrong team one."""
def grav_tether_lock (source, target, offset=None, overspeed=None):
    """Rigid grab: target locked onto the source's offset point (cargo, hangar recovery).
    
    A lock opened across a GAP winches in first. Rigid means stiffness 0, and stiffness 0
    has no rate limit anywhere - engine or mock - so the connection puts the load on the
    source point the same tick it is made. Close up (a hangar recovery, the case this mode
    was written for) that is exactly right and nothing changes. At range it is a teleport,
    and once :func:`grav_tether_set_range_limit` let a lock open from thousands of units
    away it became reachable from the shipped Weapons hold-click. Worse in the one case
    that reads as broken rather than cheap: the mass rule flips a grab on a starbase, so
    the STATION is the puller and the PLAYER is what gets snapped across the gap.
    
    So beyond :data:`LOCK_GRAB_DISTANCE` the beam engages at
    :data:`LOCK_WINCH_STIFFNESS` - a lagged, rate-limited pull - and ``_tick_lock``
    hardens it to rigid once the load is actually in reach, emitting
    ``grav_tether_locked``. Same end state, arrived at rather than jumped to."""
def grav_tether_lock_grab_distance ():
    """The rigid-grab distance in force."""
def grav_tether_mass (obj):
    """What this object weighs, via the installed provider. Never returns 0."""
def grav_tether_mass_ratio (source, target):
    """target mass / source mass. >1 means the LOAD is the heavier end.
    
    The one number the constraints layer turns on: who drags whom, and how much it costs
    the puller."""
def grav_tether_mode (source, target):
    """Which preset opened this tether - ``"lock"``, ``"tow"``, ``"swing"``, ``"reel"``
    - or None when the pair is not tethered."""
def grav_tether_out_of_reach (source, target):
    """Whether these two are too far apart to open a tether."""
def grav_tether_partner (obj):
    """The id on the other end of ``obj``'s tether, or 0 when it is free.
    
    The MAST-friendly half of :func:`grav_tether_status`: an id is something a route can
    hand straight to ``to_object`` / ``has_any_role`` without unpacking a dict."""
def grav_tether_pull_bonus (source):
    """This ship's hauling multiplier. Never returns 0 and never raises."""
def grav_tether_pull_mass (target):
    """Combined mass of every ship hauling ``target``, tug rigs included.
    
    A load does not know how many ropes are on it - it knows how hard it is being pulled.
    So the number that matters to a haul is the total on the beam, not any one tug's
    share, and this is what makes a second hull worth bringing.
    
    Falls back to :data:`DEFAULT_MASS` when nothing is hauling it, so a caller asking
    about a free object gets the same neutral answer :func:`grav_tether_mass` gives."""
def grav_tether_pullers_of (target):
    """The ships actually HAULING ``target`` - what a readout counts.
    
    :func:`grav_tether_sources_of` minus two kinds of beam that are registered as sources
    and are pulling nothing. A SWING's source is the anchor, and a rock does not haul. A
    MASS-REVERSED tether's registered source is the LOAD - the engine is moving them.
    Counting either inflates the crew and makes the haul look lighter than it is."""
def grav_tether_range_limit ():
    """The engage range in force, or None."""
def grav_tether_reel (source, target, rate=50.0, stiffness=5.0, offset=None, overspeed=None):
    """Reel the load in: start the rope at the current separation and ramp it to 0,
    then emit ``grav_tether_reeled`` for the caller to hand off (collect / dock)."""
def grav_tether_release (source, target):
    """Break a single tether (source no longer pulls target). Safe if none exists."""
def grav_tether_release_all (source):
    """Break every tether where ``source`` is the puller."""
def grav_tether_release_any (obj):
    """Release every tether obj is part of, at either end."""
def grav_tether_release_between (a, b):
    """Break the tether between these two, whichever end opened it. Safe if none exists."""
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
def grav_tether_set_lock_grab_distance (distance):
    """How close a Grav Lock may go rigid from. Beyond it, a lock winches in first."""
def grav_tether_set_mass_fn (fn):
    """Install (or clear with None) the mass provider: fn(id) -> float.
    
    Without one every object weighs :data:`DEFAULT_MASS`, so the mass rules below all
    reduce to "evenly matched" - no gating, no drag. That is deliberate: a library that
    guessed at mass would be confidently wrong, and a mission that has not said what
    things weigh should get the un-gated behavior it had before."""
def grav_tether_set_overspeed_default (mode):
    """Set the module default overspeed mode (cap / snap / off) for new tethers."""
def grav_tether_set_pull_bonus_fn (fn):
    """Install (or clear with None) the hauling-bonus provider: fn(id) -> multiplier.
    
    1.0 is an ordinary hull. This is how a mission gives a ship a heavy-tug rig without
    lying about what it weighs.
    
    DELIBERATELY NOT FOLDED INTO THE MASS PROVIDER, even though the arithmetic would be
    identical, because mass answers three other questions and a tug rig should change
    none of them: whether a Grav Lock reverses onto you (:data:`MASS_REVERSE_RATIO`),
    what you cost somebody ELSE to tow, and - for a mission that prices salvage by mass -
    what your own wreck is worth. Better towing gear that quietly made your hulk more
    valuable would be a bug nobody would ever trace back to the rig."""
def grav_tether_set_range_limit (distance, snap_factor=1.5):
    """Set how far a tether can reach to open, and how far it stretches before it snaps.
    
    ``None`` clears the rule and restores the library's original unlimited reach."""
def grav_tether_set_tow_energy_cost (per_mass_per_tick):
    """Energy the puller spends per tick, per unit of towed mass. 0 = free."""
def grav_tether_sources_of (target):
    """List the source ids currently tethering ``target`` (a tow/lock source, or a swing
    anchor). Lets a mission see who is working a shared quest target (claim-on-tether)."""
def grav_tether_status (obj):
    """What ``obj`` is tethered to and how, or None when it is free.
    
    One call rather than three, because every readout wants the same three facts at
    once: what is on the other end, what the beam is doing, and which end WE are on. A
    ship can be the puller (tow/reel/lock) or the pulled (swing, or a grab that mass
    reversed), and a display that assumes the first is wrong exactly when being tethered
    matters most.
    
    Returns a dict ``{"partner", "mode", "role", "source", "target", "strain",
    "pullers"}`` - ``role`` is ``"source"`` when obj is the puller, ``"target"`` when it
    is the load. The FIRST tether found; a ship holding several is unusual and a
    one-square readout has room for one anyway.
    
    ``strain`` and ``pullers`` are here so a console can say what a haul is costing
    without reaching into this module's internals - the whole reason a tow felt broken
    was that nothing surfaced them. ``strain`` is deliberately the BAND, not the ratio:
    a readout keyed on a per-tick number repaints itself to pieces."""
def grav_tether_strain (source, target):
    """How hard the ships on ``target`` are working, as a word a readout can print.
    
    ``none`` / ``light`` / ``heavy`` / ``overloaded``. The boundaries are the points where
    the mechanics actually change, not round numbers: ``light`` ends where drag stops
    growing (past there extra mass no longer costs extra drive - only lag and power), and
    ``overloaded`` is where the beam's own sluggishness, not the drive penalty, is what is
    beating the crew.
    
    A BAND rather than the raw ratio on purpose. The ratio moves whenever anything joins
    or leaves; a band moves about once a haul, which is what lets it drive both an
    edge-triggered signal and a console's repaint key without tearing the panel down."""
def grav_tether_swing (anchor, ship, rope_len, stiffness=1.0, overspeed=None):
    """Fighter swing (SECONDARY): hold the ship on a CIRCLE of radius rope_len around the
    anchor so it orbits on its own throttle. A plain rope-toggle pulls toward the anchor
    *center*, which has no centrifugal balance and spirals the ship in (measured 758→663).
    Instead each tick we aim the pull at the point on the circle at the ship's CURRENT
    bearing — a purely radial correction that holds the radius without killing tangential
    motion. Engine-confirmed a player hull can be tractor-pulled; final feel is a fly-it."""
def grav_tether_target_too_fast (target):
    """Whether this target is moving too fast to get hold of."""
def grav_tether_targets_of (source):
    """List the target ids ``source`` is currently pulling. Mirror of
    :func:`grav_tether_sources_of`."""
def grav_tether_tick (t=None):
    """Runs on the TickDispatcher (~7.5/sim-sec in-engine, 6 in the mock - see
    DEFAULT_REEL_RATE) while any tether is live; also directly
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
def has_any_role (so, roles):
    """Return whether an agent holds at least one of the given roles.
    
    Args:
        so (Agent | int): Agent ID or object.
        roles (str): A comma-separated list of role names.
    
    Returns:
        bool: ``True`` if the agent has one or more of the roles."""
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
