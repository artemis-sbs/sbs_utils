"""grav_tether — attach a beam between two space objects to lock / tow / reel a load.

Thin wrappers over the ENGINE-native tractor system (``sim.AddTractorConnection`` /
``DeleteTractorConnection`` / ``GetTractorConnection``) plus the mission-facing behavior
the raw API doesn't provide: the mode presets (lock / tow / reel), a reel ramp, and the
canonical **impulse-only** enforcement.

Confirmed in-engine (Phase 0 spike, GRAV_TETHER_PLAN.md):
  * ``AddTractorConnection(src, tgt, offset_point, pull_distance)`` pulls ``tgt`` toward
    ``src + offset_point``; ``pull_distance`` is a **rope rest-length** (the target
    settles at that distance).
  * the connection's ``.offset`` float is a **pull SPEED** dial, engine-measured at
    ``offset x 30.2`` u/s, linear in offset and linear in time: 0 = rigid lock (the
    target is placed on the point in one tick), ~5 = a good taut tow at ~151 u/s, and
    higher pulls FASTER. Earlier notes here called it stiffness and said higher was
    "looser/laggier" - never measured, and backwards. See LM_TestRange map
    test_tractor_calibrate.
  * a tether can only hold at **impulse** — warp (playerThrottle > 1) outruns the
    rate-limited pull. Canonical (old-game Arena a28 precedent). Enforced here per
    tether: ``cap`` (default, governs the source back to impulse) or ``snap`` (breaks
    the tether and drops the load).

NOTE: the cosmos_dev mock STORES connections but does not simulate the pull, so the
physics is engine-verified; the registry / enforcer / reel logic below is Python and IS
unit-tested against the mock.

THE OFFSET POINT IS SOURCE-RELATIVE - it rotates with the hull. Engine-measured
(LM_TestRange/maps/test_tractor_mount.mast): AddTractorConnection with an offset held a
target at exactly 200u and exactly 0 deg off the source's nose through a 51 deg turn.
Older notes here and in GRAV_TETHER_PLAN.md called it "world-fixed"; that was only ever
true of the case this module uses, because a tow passes NO offset and the load therefore
reels to the source's own position. The wrong wording cost a real design decision once.
To bolt something ONTO a hull rather than drag it behind one, use
sbs_utils.procedural.mount - which shares the engine call but deliberately not this
registry, since _enforce_impulse would cap the carrying ship to impulse.
"""

import logging
import math

from ..helpers import FrameContext
from ..tickdispatcher import TickDispatcher
from .query import to_id, to_object, object_exists, get_data_set_value
from .roles import has_any_role
from .signal import signal_emit

# Sensible defaults from the Phase 0 spike.
DEFAULT_TOW_STIFFNESS = 5.0
# A 0.1s TickDispatcher interval does NOT fire ten times a sim-second. TickTask._update
# measures its delay in tick-counter units (30/sim-sec in both hosts), but dispatch_tick
# is called 15x/sim-sec in the engine and 6x in the mock, so a 3-tick interval lands ~7.5
# times a second on a bridge and 6 headless. Every "per tick" number here is per one of
# those, which also means the mock bills a haul about 20% less power than the engine does.
DEFAULT_REEL_RATE = 50.0          # rope-length reduced per tick -> ~375 u/s in-engine
_TICK_SECONDS = 0.1

# Overspeed enforcement mode when a source ship pushes past impulse while towing.
OVERSPEED_CAP = "cap"             # clamp the source back to impulse (never lose the tow)
OVERSPEED_SNAP = "snap"           # break the tether + drop the load
OVERSPEED_OFF = "off"             # no enforcement
_default_overspeed = OVERSPEED_CAP

# Which preset opened a tether. Carried in the registry rather than inferred from the
# state keys, because a UI has to be able to SAY what the beam is doing - "TOW" and
# "SWING" are the same rope-hold to the physics and completely different to a crew.
MODE_LOCK = "lock"
MODE_TOW = "tow"
MODE_SWING = "swing"
MODE_REEL = "reel"

# (src_id, tgt_id) -> state we must keep ourselves (the connection object exposes only
# .offset, not the offset_point / pull_distance we need to re-attach for a reel).
_TETHERS = {}
_tick_task = None

# Optional veto checked before every NEW tether: fn(source_id, target_id) -> True to allow,
# False to deny. Lets a mission enforce ownership (e.g. a non-owner can't tether an owned
# quest target) without the library knowing anything about quests. None = allow all.
_attach_policy = None


# Mass provider for the constraints layer. shipData has NO mass field, and the obvious
# proxies do not order ships correctly (exclusionradius puts a fighter and a shuttle both
# at 25), so a MISSION owns the numbers and installs them here - the same shape as the
# attach veto below. The default keeps the library usable on its own: everything weighs
# the same, so tug-of-war is a no-op rather than a wrong answer.
_mass_fn = None

#: What an object weighs when nothing better is known. Units are RELATIVE - only the
#: ratio between two ends of a tether is ever used.
DEFAULT_MASS = 1.0

#: How much heavier the load must be before it drags YOU instead. 2.0 = anything twice
#: your mass wins. Below this the puller wins and merely pays for it in drag.
#:
#: A LOCK and a REEL reverse; a TOW deliberately does not. Grabbing a starbase rigidly
#: means going where the starbase goes, and hauling one means straining against it - two
#: different verbs, and a crew that picked "Tow" asked to be the one doing the pulling.
#: So a tow never flips, and pays for the privilege in lag, drag and power instead.
MASS_REVERSE_RATIO = 2.0

#: Exponent on the mass ratio when a tow scales its pull speed. 0.5 = square root.
#:
#: The dial this divides is ``con.offset``, and it is a SPEED, engine-measured: the target
#: closes at ``offset x 30.2`` units per second, linearly in both offset and time
#: (LM_TestRange map test_tractor_calibrate, offsets 1-80 read at 10s and 20s). So a
#: heavier load gets a SMALLER offset and reels in slower. The engine API calls the field
#: "stiffness" and older notes in this module called higher values "looser and laggier" -
#: that was never measured and is backwards, which is why the first version of this
#: function multiplied and made a starbase arrive four times faster than a fighter.
#:
#: SUBLINEAR ON PURPOSE. Linear would put a 66:1 starbase grab at a fifteenth of the base
#: speed - slow enough that the power bill cuts the beam before the load has gone
#: anywhere, so "you can drag a starbase" stops being true. A root curve is monotone the
#: whole way, so every extra hull on the beam is worth bringing.
TOW_LAG_CURVE = 0.5

#: Floor on the scaled pull, as a fraction of the tow's base stiffness. An eighth is
#: reached at a ratio of 64 - a lone cruiser on a command starbase, i.e. exactly the case
#: meant to be at the wall. Every realistic TEAM lands well above it, so the floor is a
#: safety rail and never the mechanic.
#:
#: It has to be strictly ABOVE ZERO, and that is not a rounding nicety: offset 0 is the
#: rigid case, and a rigid connection puts the load on the source point in a single tick.
#: A mass table is a mission's to write and nothing stops it holding 100000 for a planet;
#: without this floor that ratio would divide the dial to nothing and turn the gentlest
#: possible tow into a teleport.
TOW_LAG_MIN_SCALE = 0.125

#: Above this throttle a target is moving too fast to get hold of - None disables the
#: rule. Off in the library and switched on by the mission, because "can you grab a ship
#: under power" is a game-balance question, not a physics one. Turning it on is what ties
#: the tether to the rest of Weapons: cripple the engines first, THEN grab.
_grab_speed_limit = None

#: Energy the puller spends per tick per unit of towed mass. 0 disables it. Gives
#: Engineering a stake - a long haul competes with shields and weapons for power.
_tow_energy_cost = 0.0

#: How far a tether can REACH to open. None = no rule, which is what the library shipped
#: with: a gunner could tether something 30,000u off the tactical picture. The NUMBER is a
#: game-balance question and belongs to a mission, so the library only carries the rule.
_range_limit = None

#: How far past its hold distance a beam stretches before it lets go.
#:
#: NOT measured against rope_len alone, which is the tempting reading and is wrong: a
#: rope-toggle tow is SUPPOSED to sit beyond its rope - that is the state in which the pull
#: engages - so a tow at rope 500 reeling a load in from 2000 would snap itself on the
#: first tick. The hold distance is therefore the LONGER of the rope and the engage range:
#: a beam breaks at half again the distance it could have opened from, and a rope longer
#: than that reach (a wide slingshot arc) is measured against its own rope instead.
#:
#: The rule only exists while an engage range does. Without one there is no distance a
#: tether is "too far" from, and the library keeps the unlimited behavior it shipped with.
SNAP_RANGE_FACTOR = 1.5
_snap_factor = SNAP_RANGE_FACTOR

#: How close a rigid Grav Lock may CLOSE from. A rigid connection (stiffness 0) has no
#: rate limit - the engine puts the load on the source point the same tick - so opening
#: one across a gap is a TELEPORT, not a grab. Beyond this a lock winches in on a lagged
#: pull first (:data:`LOCK_WINCH_STIFFNESS`) and goes rigid only once the gap is closed.
#:
#: The bug this exists for: a range limit made a lock at 7000u legal, and the mass rule
#: made the STATION the puller - so the player was snapped across 7000u onto the starbase
#: the instant they clicked. Rigid was always a snap; nothing used to be far enough away
#: for it to show.
LOCK_GRAB_DISTANCE = 100.0
_lock_grab_distance = LOCK_GRAB_DISTANCE

#: Stiffness the winch runs at while a lock is still closing. Any non-zero value is
#: rate-limited by the engine; this is the same taut-tow dial a Tow uses.
LOCK_WINCH_STIFFNESS = DEFAULT_TOW_STIFFNESS

#: Roles that can only ever be an ANCHOR - something you hang a rope FROM, never
#: something you pull. A black hole, a planet or a nebula does not move for a tractor
#: beam, and a beam that claims to be pulling one is an expensive lie: the source is
#: capped to impulse (_enforce_impulse) for a haul that can never arrive, held next to
#: the thing that kills it. A rigid Grav Lock on a black hole was reachable from the
#: shipped Weapons hold-click and took whole games down that way.
#:
#: NOT "all terrain": towing an asteroid and towing a derelict are shipped, wanted
#: mechanics. Only the bodies nothing could plausibly drag are listed.
ANCHOR_ROLES = "black_hole,planet,nebula"
_anchor_roles = ANCHOR_ROLES


def grav_tether_set_mass_fn(fn):
    """Install (or clear with None) the mass provider: fn(id) -> float.

    Without one every object weighs :data:`DEFAULT_MASS`, so the mass rules below all
    reduce to "evenly matched" - no gating, no drag. That is deliberate: a library that
    guessed at mass would be confidently wrong, and a mission that has not said what
    things weigh should get the un-gated behavior it had before.
    """
    global _mass_fn
    _mass_fn = fn


#: Optional provider for a ship's HAULING multiplier: fn(source_id) -> float.
#: Separate from the mass provider on purpose - see grav_tether_set_pull_bonus_fn.
_pull_bonus_fn = None


def grav_tether_set_pull_bonus_fn(fn):
    """Install (or clear with None) the hauling-bonus provider: fn(id) -> multiplier.

    1.0 is an ordinary hull. This is how a mission gives a ship a heavy-tug rig without
    lying about what it weighs.

    DELIBERATELY NOT FOLDED INTO THE MASS PROVIDER, even though the arithmetic would be
    identical, because mass answers three other questions and a tug rig should change
    none of them: whether a Grav Lock reverses onto you (:data:`MASS_REVERSE_RATIO`),
    what you cost somebody ELSE to tow, and - for a mission that prices salvage by mass -
    what your own wreck is worth. Better towing gear that quietly made your hulk more
    valuable would be a bug nobody would ever trace back to the rig.
    """
    global _pull_bonus_fn
    _pull_bonus_fn = fn


def grav_tether_pull_bonus(source):
    """This ship's hauling multiplier. Never returns 0 and never raises."""
    if _pull_bonus_fn is None:
        return 1.0
    try:
        b = float(_pull_bonus_fn(to_id(source)))
    except Exception:
        return 1.0
    return b if b > 0.0 else 1.0


def grav_tether_mass(obj):
    """What this object weighs, via the installed provider. Never returns 0."""
    oid = to_id(obj)
    if oid is None or _mass_fn is None:
        return DEFAULT_MASS
    try:
        m = float(_mass_fn(oid))
    except Exception:
        return DEFAULT_MASS
    return m if m > 0 else DEFAULT_MASS


def grav_tether_mass_ratio(source, target):
    """target mass / source mass. >1 means the LOAD is the heavier end.

    The one number the constraints layer turns on: who drags whom, and how much it costs
    the puller.
    """
    return grav_tether_mass(target) / max(0.0001, grav_tether_mass(source))


def grav_tether_pullers_of(target):
    """The ships actually HAULING ``target`` - what a readout counts.

    :func:`grav_tether_sources_of` minus two kinds of beam that are registered as sources
    and are pulling nothing. A SWING's source is the anchor, and a rock does not haul. A
    MASS-REVERSED tether's registered source is the LOAD - the engine is moving them.
    Counting either inflates the crew and makes the haul look lighter than it is.
    """
    tid = to_id(target)
    return [src for (src, tgt), st in _TETHERS.items()
            if tgt == tid and not st.get("swing") and not st.get("reversed")]


def grav_tether_pull_mass(target):
    """Combined mass of every ship hauling ``target``, tug rigs included.

    A load does not know how many ropes are on it - it knows how hard it is being pulled.
    So the number that matters to a haul is the total on the beam, not any one tug's
    share, and this is what makes a second hull worth bringing.

    Falls back to :data:`DEFAULT_MASS` when nothing is hauling it, so a caller asking
    about a free object gets the same neutral answer :func:`grav_tether_mass` gives.
    """
    total = sum(grav_tether_mass(p) * grav_tether_pull_bonus(p)
                for p in grav_tether_pullers_of(target))
    return total if total > 0 else DEFAULT_MASS


def grav_tether_load_ratio(source, target):
    """How outmatched the ships on ``target`` are, all of them together.

    The team-aware sibling of :func:`grav_tether_mass_ratio`, which stays a ONE-ship
    question on purpose: who gets reversed is about the ship that grabbed, while how hard
    the haul is is about every beam on the load. Every cost a tow pays comes from this,
    so a tug joining lightens the haul for everyone already on it.

    ``source`` is only the fallback: when nothing is registered as hauling the target -
    a caller asking before the tether exists, or from the reversed end - it stands in for
    the crew, so the answer is the plain one-ship ratio rather than a wrong team one.
    """
    if grav_tether_pullers_of(target):
        pull = grav_tether_pull_mass(target)
    else:
        pull = grav_tether_mass(source) * grav_tether_pull_bonus(source)
    return grav_tether_mass(target) / max(0.0001, pull)


def grav_tether_set_anchor_roles(roles):
    """Set the roles that may never be PULLED (comma-separated, or "" to allow all).

    A mission that wants the library default back passes :data:`ANCHOR_ROLES`.
    """
    global _anchor_roles
    _anchor_roles = roles or ""


def grav_tether_is_anchor(obj):
    """Whether this object can only ever be the anchor end of a tether."""
    return bool(_anchor_roles) and has_any_role(to_id(obj), _anchor_roles)


def grav_tether_set_range_limit(distance, snap_factor=SNAP_RANGE_FACTOR):
    """Set how far a tether can reach to open, and how far it stretches before it snaps.

    ``None`` clears the rule and restores the library's original unlimited reach.
    """
    global _range_limit, _snap_factor
    _range_limit = None if distance is None else float(distance)
    _snap_factor = float(snap_factor or SNAP_RANGE_FACTOR)


def grav_tether_range_limit():
    """The engage range in force, or None."""
    return _range_limit


def grav_tether_set_lock_grab_distance(distance):
    """How close a Grav Lock may go rigid from. Beyond it, a lock winches in first."""
    global _lock_grab_distance
    _lock_grab_distance = float(LOCK_GRAB_DISTANCE if distance is None else distance)


def grav_tether_lock_grab_distance():
    """The rigid-grab distance in force."""
    return _lock_grab_distance


def grav_tether_out_of_reach(source, target):
    """Whether these two are too far apart to open a tether."""
    if _range_limit is None:
        return False
    so, to = to_object(source), to_object(target)
    if so is None or to is None:
        return False
    return _distance(so, to) > _range_limit


def _hold_distance(st):
    """The distance this tether is entitled to hold across, or None when no rule applies."""
    if _range_limit is None:
        return None
    return max(float(st.get("rope_len") or 0.0), _range_limit)


def _over_stretched(src, tgt, st):
    """Whether a live tether has been pulled past breaking."""
    hold = _hold_distance(st)
    if not hold:
        return False
    so, to = to_object(src), to_object(tgt)
    if so is None or to is None:
        return False
    return _distance(so, to) > hold * _snap_factor


def grav_tether_set_grab_speed_limit(limit):
    """Refuse a grab on anything moving faster than `limit` throttle. None = no rule."""
    global _grab_speed_limit
    _grab_speed_limit = limit


def grav_tether_set_tow_energy_cost(per_mass_per_tick):
    """Energy the puller spends per tick, per unit of towed mass. 0 = free."""
    global _tow_energy_cost
    _tow_energy_cost = float(per_mass_per_tick or 0.0)


def grav_tether_target_too_fast(target):
    """Whether this target is moving too fast to get hold of."""
    if _grab_speed_limit is None:
        return False
    thr = get_data_set_value(to_id(target), "playerThrottle")
    if thr is None:
        thr = get_data_set_value(to_id(target), "throttle")
    return thr is not None and float(thr) > float(_grab_speed_limit)


def _spend_tow_energy(src, tgt, st):
    """Charge the puller for its SHARE of holding a load. Returns True if it snapped dry.

    Running a ship's reserves to nothing would be a worse mechanic than making the haul
    expensive, so an empty tank BREAKS the beam and drops the load rather than pinning the
    ship at zero energy.

    THE SHARE IS WHAT MAKES A SECOND TUG WORTH CALLING. The load's bill is fixed by what
    it weighs; each puller pays it in proportion to its own mass. Charge every ship the
    FULL bill instead - which is what this did - and four hulls on one starbase each drain
    at the solo rate and all four cut out at the same moment: the fleet spends four times
    the power for not one extra second of haul. Shared, a lone tug pays exactly what it
    always did and four of them each last four times as long.
    """
    if _tow_energy_cost <= 0.0 or st.get("swing"):
        return False
    so = to_object(src)
    if so is None:
        return False
    try:
        have = so.data_set.get("energy", 0) or 0.0
    except Exception:
        return False
    if have <= 0.0:
        return False                      # nothing to spend from (an NPC): tow is free
    mine = grav_tether_mass(src) * grav_tether_pull_bonus(src)
    share = mine / max(0.0001, grav_tether_pull_mass(tgt))
    cost = _tow_energy_cost * grav_tether_mass(tgt) * min(1.0, share)
    left = float(have) - cost
    if left <= 0.0:
        so.data_set.set("energy", 0.0, 0)
        grav_tether_release(src, tgt)
        signal_emit("grav_tether_dry", {"SOURCE_ID": src, "TARGET_ID": tgt})
        return True
    so.data_set.set("energy", left, 0)
    return False


def grav_tether_set_attach_policy(fn):
    """Install (or clear with None) the attach veto callback. An attach whose
    fn(source_id, target_id) returns False is refused (attach returns None)."""
    global _attach_policy
    _attach_policy = fn


def _attach_allowed(src, tgt):
    return _attach_policy is None or _attach_policy(src, tgt)


def _attach_guard(src, tgt):
    """Every refusal rule, in one place. True when the tether may be created.

    `tgt` is always the end of the rope - the load for a lock/tow/reel, and the SHIP for
    a swing, where the anchor is the source. That is what lets one rule cover both: a
    black hole may anchor a slingshot and may never be dragged.
    """
    if src is None or tgt is None or src == 0 or tgt == 0:
        return False
    if not _attach_allowed(src, tgt):
        return False
    if grav_tether_is_anchor(tgt):
        signal_emit("grav_tether_immovable", {"SOURCE_ID": src, "TARGET_ID": tgt})
        return False
    if grav_tether_out_of_reach(src, tgt):
        signal_emit("grav_tether_out_of_reach",
                    {"SOURCE_ID": src, "TARGET_ID": tgt, "RANGE": _range_limit})
        return False
    if grav_tether_target_too_fast(tgt):
        signal_emit("grav_tether_too_fast", {"SOURCE_ID": src, "TARGET_ID": tgt})
        return False
    return True


def _sim():
    return FrameContext.sim


def _sbs():
    return FrameContext.context.sbs


def _to_sbs_vec(offset):
    """Accept None / an sbs.vec3 / a sbs_utils Vec3 / an (x,y,z) tuple."""
    sbs = _sbs()
    if offset is None:
        return sbs.vec3(0.0, 0.0, 0.0)
    x = getattr(offset, "x", None)
    if x is not None:
        return sbs.vec3(offset.x, offset.y, offset.z)
    return sbs.vec3(offset[0], offset[1], offset[2])


def _distance(a_obj, b_obj):
    pa = a_obj.pos
    pb = b_obj.pos
    dx = pa.x - pb.x
    dy = pa.y - pb.y
    dz = pa.z - pb.z
    return math.sqrt(dx * dx + dy * dy + dz * dz)


def grav_tether_set_overspeed_default(mode):
    """Set the module default overspeed mode (cap / snap / off) for new tethers."""
    global _default_overspeed
    _default_overspeed = mode


def grav_tether_attach(source, target, offset=None, stiffness=0.0, pull_distance=0.0,
                       overspeed=None):
    """Open (or replace) a tether so ``source`` pulls ``target``.

    offset        - point (relative to source) the target is pulled toward.
    stiffness     - the connection's .offset dial: 0 = rigid lock, ~5 = taut tow.
    pull_distance - rope rest-length; the target settles at this distance.
    overspeed     - per-tether enforcement mode; None uses the module default.
    Returns the tractor_connection, or None if either object is missing.
    """
    src = to_id(source)
    tgt = to_id(target)
    if not _attach_guard(src, tgt):
        return None
    sim = _sim()
    # WHO ACTUALLY GETS PULLED is decided by mass, not by who pressed the button. Grab
    # something far heavier than you and the engine connection is built the other way
    # round, so the starbase holds station and reels YOU in. That is a better answer than
    # refusing the grab: a refusal teaches nothing, and being dragged toward a station is
    # a moment. The registry key stays as the CALLER wrote it, so release/get/has all
    # still work in the caller's terms; only the engine pair is flipped.
    reverse = grav_tether_mass_ratio(src, tgt) >= MASS_REVERSE_RATIO
    a, b = (tgt, src) if reverse else (src, tgt)
    sim.DeleteTractorConnection(a, b)
    con = sim.AddTractorConnection(a, b, _to_sbs_vec(offset), float(pull_distance))
    con.offset = float(stiffness)
    _TETHERS[(src, tgt)] = {
        "offset": offset,
        "stiffness": float(stiffness),
        "pull": float(pull_distance),
        "overspeed": overspeed if overspeed is not None else _default_overspeed,
        "reel_rate": 0.0,
        "reversed": reverse,
        "mode": MODE_LOCK,
    }
    _ensure_tick()
    return con


def grav_tether_release(source, target):
    """Break a single tether (source no longer pulls target). Safe if none exists."""
    src = to_id(source)
    tgt = to_id(target)
    if src is None or tgt is None:
        return
    _delete_connection(src, tgt)
    _TETHERS.pop((src, tgt), None)
    _drag_recheck(src)
    _maybe_stop_tick()


def _conn_pair(src, tgt):
    """The ENGINE pair for a registry key, whichever way round the mass rule built it.

    A mass-reversed tether was created as (target, source), so touching only the pair the
    caller knows about leaves the real connection live and the load still held. EVERY
    engine call for a registered tether goes through here - the reel ramp and the rope
    toggle used to re-add the raw (src, tgt) each tick, which on a reversed tether left
    the reversed connection pulling AND built a second one facing the other way.
    """
    st = _TETHERS.get((src, tgt))
    return (tgt, src) if (st is not None and st.get("reversed")) else (src, tgt)


def _delete_connection(src, tgt):
    """Drop the ENGINE connection for a registry pair, whichever way round it was built."""
    a, b = _conn_pair(src, tgt)
    try:
        _sim().DeleteTractorConnection(a, b)
    except Exception:
        pass


def _get_connection(src, tgt):
    """The live ENGINE connection for a registry pair, or None."""
    a, b = _conn_pair(src, tgt)
    return _sim().GetTractorConnection(a, b)


def _add_connection(src, tgt, offset, pull):
    """Create the ENGINE connection for a registry pair. May return None: the engine can
    refuse one (a static body is the likely case), and dereferencing that None inside the
    tick is how a single tether used to pause the whole sim."""
    a, b = _conn_pair(src, tgt)
    return _sim().AddTractorConnection(a, b, offset, float(pull))


def _drag_recheck(src):
    """Lift the tow drag, and re-arm any tether this ship still holds.

    A ship towing two things that lets one go should end up dragged by what is LEFT, not
    by what it dropped and not by nothing. Clearing the cached amount makes the next tick
    recompute from whatever remains.
    """
    _release_drag(src)
    for key, st in _TETHERS.items():
        if key[0] == src:
            st.pop("drag", None)


def grav_tether_release_all(source):
    """Break every tether where ``source`` is the puller."""
    src = to_id(source)
    for key in [k for k in _TETHERS if k[0] == src]:
        _delete_connection(key[0], key[1])
        _TETHERS.pop(key, None)
    _drag_recheck(src)
    _maybe_stop_tick()


def grav_tether_sources_of(target):
    """List the source ids currently tethering ``target`` (a tow/lock source, or a swing
    anchor). Lets a mission see who is working a shared quest target (claim-on-tether)."""
    tid = to_id(target)
    return [k[0] for k in _TETHERS if k[1] == tid]


def grav_tether_has(source, target):
    """True if this exact PAIR is tethered — ask this, not :func:`grav_tether_get`.

    `grav_tether_get` returns the live ENGINE connection, and a Tow is a rope-TOGGLE: it
    deletes the connection whenever the load is inside the rope length and re-adds it when
    the load drifts out. So `get` reads None for most of a perfectly good tow, and a UI
    gated on it offers "Tow" to something already under tow and never offers "Release".

    Use `get` only when you want the engine object itself (to read `.offset`).
    """
    src, tgt = to_id(source), to_id(target)
    return (src, tgt) in _TETHERS


def grav_tether_involves(obj):
    """True if obj is either end (source or target) of any live tether — for a one-button
    toggle where the ship may be the puller (tow/reel) or the pulled (swing).

    Registry-based, so it is honest during a rope-toggle tow (see :func:`grav_tether_has`).
    """
    oid = to_id(obj)
    return any(oid == k[0] or oid == k[1] for k in _TETHERS)


def grav_tether_targets_of(source):
    """List the target ids ``source`` is currently pulling. Mirror of
    :func:`grav_tether_sources_of`."""
    sid = to_id(source)
    return [k[1] for k in _TETHERS if k[0] == sid]


def grav_tether_mode(source, target):
    """Which preset opened this tether - ``"lock"``, ``"tow"``, ``"swing"``, ``"reel"``
    - or None when the pair is not tethered."""
    src, tgt = to_id(source), to_id(target)
    st = _TETHERS.get((src, tgt))
    return None if st is None else st.get("mode")


def grav_tether_status(obj):
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
    a readout keyed on a per-tick number repaints itself to pieces.
    """
    oid = to_id(obj)
    if oid is None:
        return None
    for (src, tgt), st in _TETHERS.items():
        if oid == src or oid == tgt:
            return {"partner": tgt if oid == src else src,
                    "mode": st.get("mode"),
                    "role": "source" if oid == src else "target",
                    "source": src, "target": tgt,
                    "strain": grav_tether_strain(src, tgt),
                    "pullers": len(grav_tether_pullers_of(tgt))}
    return None


def grav_tether_partner(obj):
    """The id on the other end of ``obj``'s tether, or 0 when it is free.

    The MAST-friendly half of :func:`grav_tether_status`: an id is something a route can
    hand straight to ``to_object`` / ``has_any_role`` without unpacking a dict.
    """
    st = grav_tether_status(obj)
    return 0 if st is None else st["partner"]


def grav_tether_release_any(obj):
    """Release every tether obj is part of, at either end."""
    oid = to_id(obj)
    for k in [k for k in _TETHERS if k[0] == oid or k[1] == oid]:
        _delete_connection(k[0], k[1])
        _TETHERS.pop(k, None)
        _drag_recheck(k[0])
    _maybe_stop_tick()


def grav_tether_between(a, b):
    """Whether these two are tethered to each other, whichever way round.

    `grav_tether_has` is directional, and a SWING is registered the other way up (the
    anchor is the source and the ship is the load). So a menu that asks `has(me, that)`
    is blind to a swing it opened itself: it goes on offering the grab and never offers
    Release, and the crew cannot let go. Ask this instead whenever the question is "is
    there a beam between these two", not "am I the puller".
    """
    aid, bid = to_id(a), to_id(b)
    if aid is None or bid is None:
        return False
    return (aid, bid) in _TETHERS or (bid, aid) in _TETHERS


def grav_tether_release_between(a, b):
    """Break the tether between these two, whichever end opened it. Safe if none exists."""
    grav_tether_release(a, b)
    grav_tether_release(b, a)


def grav_tether_get(source, target):
    """Return the live tractor_connection for the pair, or None."""
    src = to_id(source)
    tgt = to_id(target)
    if src is None or tgt is None:
        return _sim().GetTractorConnection(src or 0, tgt or 0)
    return _sim().GetTractorConnection(src, tgt)


def grav_tether_clear_all():
    """Drop all tethers (fresh mission / test reset).

    Drops OUR tethers one by one rather than calling ClearTractorConnections(), which is
    global: the engine has a single tractor pool, and other systems build connections in
    it that are not tethers. `procedural.mount` welds a turret to a hull with one, and a
    global clear silently unwelded every mount while mount's own bookkeeping went on
    insisting they were attached. Deleting only what this module registered keeps the two
    uses independent.

    Tolerates having no sim: this runs from reset_mission_state(), which can fire with no
    frame context at all, and dropping our own state must never depend on the engine
    being there. The engine-side connections die with the old sim regardless.
    """
    sim = None
    try:
        sim = _sim()
    except Exception:
        sim = None
    if sim is not None:
        for key in list(_TETHERS):
            _delete_connection(key[0], key[1])     # reversal-aware; raw pair leaked one
    for key in list(_TETHERS):
        _release_drag(key[0])                      # a cleared tether must give the drive back
    _TETHERS.clear()
    _maybe_stop_tick()


# --- mode presets ---------------------------------------------------------------

def grav_tether_lock(source, target, offset=None, overspeed=None):
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
    ``grav_tether_locked``. Same end state, arrived at rather than jumped to.
    """
    src = to_id(source)
    tgt = to_id(target)
    so = to_object(src)
    to = to_object(tgt)
    dist = _distance(so, to) if (so is not None and to is not None) else 0.0
    if dist <= _lock_grab_distance:
        return grav_tether_attach(source, target, offset=offset, stiffness=0.0,
                                  pull_distance=0.0, overspeed=overspeed)
    con = grav_tether_attach(source, target, offset=offset,
                             stiffness=LOCK_WINCH_STIFFNESS, pull_distance=dist,
                             overspeed=overspeed)
    if con is None:
        return None
    st = _TETHERS.get((src, tgt))
    if st is not None:
        st["winch"] = True          # still closing; _tick_lock hardens it on arrival
    return con


def grav_tether_tow(source, target, distance, stiffness=DEFAULT_TOW_STIFFNESS, overspeed=None):
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
    return grav_tether_rope(source, target, distance, stiffness, overspeed)


def grav_tether_rope(source, target, rope_len, stiffness=DEFAULT_TOW_STIFFNESS, overspeed=None):
    """Hold the target at ~``rope_len`` from the source via a per-tick ROPE-TOGGLE:
    beyond rope_len a stiff pull snaps it back to the circle; inside, the tether is
    released so it moves free. Engine-confirmed (data harness): a STATIC tether reels
    the target fully in regardless of pull_distance (1500 -> ~165), so holding a load
    *at* a distance REQUIRES this toggle (which held 798/801/801 at rope_len=800). Both
    Tow (source drags a trailing load) and Swing (anchor holds the ship) are this same
    rope-hold — only the source/target roles differ."""
    src = to_id(source)
    tgt = to_id(target)
    if not _attach_guard(src, tgt):
        return None
    _TETHERS[(src, tgt)] = {
        "offset": None,
        "stiffness": float(stiffness),
        "pull": float(rope_len),
        "rope_len": float(rope_len),
        "rope": True,
        "overspeed": overspeed if overspeed is not None else _default_overspeed,
        "reel_rate": 0.0,
        "mode": MODE_TOW,
    }
    _ensure_tick()
    if not _tick_rope(src, tgt, _TETHERS[(src, tgt)]):   # engage now if already taut
        grav_tether_release(src, tgt)                    # engine refused the beam
        return None
    return _get_connection(src, tgt)


def grav_tether_swing(anchor, ship, rope_len, stiffness=1.0, overspeed=None):
    """Fighter swing (SECONDARY): hold the ship on a CIRCLE of radius rope_len around the
    anchor so it orbits on its own throttle. A plain rope-toggle pulls toward the anchor
    *center*, which has no centrifugal balance and spirals the ship in (measured 758→663).
    Instead each tick we aim the pull at the point on the circle at the ship's CURRENT
    bearing — a purely radial correction that holds the radius without killing tangential
    motion. Engine-confirmed a player hull can be tractor-pulled; final feel is a fly-it."""
    src = to_id(anchor)
    tgt = to_id(ship)
    if not _attach_guard(src, tgt):
        return None
    _TETHERS[(src, tgt)] = {
        "offset": None,
        "stiffness": float(stiffness),
        "pull": float(rope_len),
        "rope_len": float(rope_len),
        "swing": True,
        "overspeed": overspeed if overspeed is not None else _default_overspeed,
        "reel_rate": 0.0,
        "mode": MODE_SWING,
    }
    _ensure_tick()
    if not _tick_swing(src, tgt, _TETHERS[(src, tgt)]):
        grav_tether_release(src, tgt)                    # engine refused the beam
        return None
    return _get_connection(src, tgt)


def grav_tether_reel(source, target, rate=DEFAULT_REEL_RATE,
                     stiffness=DEFAULT_TOW_STIFFNESS, offset=None, overspeed=None):
    """Reel the load in: start the rope at the current separation and ramp it to 0,
    then emit ``grav_tether_reeled`` for the caller to hand off (collect / dock)."""
    src = to_id(source)
    tgt = to_id(target)
    if src is None or tgt is None:
        return None
    so = to_object(src)
    to = to_object(tgt)
    dist = _distance(so, to) if (so is not None and to is not None) else 0.0
    con = grav_tether_attach(source, target, offset=offset, stiffness=stiffness,
                             pull_distance=dist, overspeed=overspeed)
    st = _TETHERS.get((src, tgt))
    if st is not None:
        st["reel_rate"] = float(rate)
        st["mode"] = MODE_REEL
    return con


# --- per-frame enforcement + reel ------------------------------------------------

def _ensure_tick():
    global _tick_task
    if _tick_task is None and _TETHERS and FrameContext.context is not None:
        _tick_task = TickDispatcher.do_interval(grav_tether_tick, _TICK_SECONDS)


def _maybe_stop_tick():
    global _tick_task
    if _tick_task is not None and not _TETHERS:
        _tick_task.stop()
        _tick_task = None


def _enforce_impulse(src, tgt, st):
    """Impulse-only rule. Returns True if the tether was snapped (removed)."""
    mode = st["overspeed"]
    if mode == OVERSPEED_OFF:
        return False
    thr = get_data_set_value(src, "playerThrottle") or 0.0
    if thr > 1.0:
        if mode == OVERSPEED_SNAP:
            grav_tether_release(src, tgt)
            return True
        so = to_object(src)
        if so is not None:
            so.data_set.set("playerThrottle", 1.0)
    return False


def _tow_lag(src, tgt, st):
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
    table, tows exactly as it always did.
    """
    base = st["stiffness"]
    if _mass_fn is None or st.get("mode") != MODE_TOW:
        return base
    ratio = grav_tether_load_ratio(src, tgt)
    if ratio <= 1.0:
        return base
    return max(base * TOW_LAG_MIN_SCALE, base / (ratio ** TOW_LAG_CURVE))


def _tick_rope(src, tgt, st):
    """Rope-toggle: taut (beyond rope_len) -> engage a stiff pull back to the circle;
    slack (inside) -> release the pull so the target moves free. Holds a load/ship at
    rope_len (a static tether would reel it fully in)."""
    so = to_object(src)
    to = to_object(tgt)
    if so is None or to is None:
        return True
    con = _get_connection(src, tgt)
    if _distance(so, to) > st["rope_len"]:
        if con is None:
            con = _add_connection(src, tgt, _to_sbs_vec(st["offset"]), st["rope_len"])
        if con is None:
            return False                     # the engine refused the beam
        con.offset = _tow_lag(src, tgt, st)
    elif con is not None:
        _delete_connection(src, tgt)
    return True


def _tick_swing(anchor, ship, st):
    """Circle-point orbit: aim the pull at the point on the rope_len circle at the ship's
    CURRENT bearing (in the XZ plane). That correction is radial-only, so it holds the
    radius while the ship's own throttle carries it around — no spiral-in, no killed
    tangential motion. Re-points every tick since the connection's offset isn't settable."""
    ao = to_object(anchor)
    so = to_object(ship)
    if ao is None or so is None:
        return True
    dx = so.pos.x - ao.pos.x
    dz = so.pos.z - ao.pos.z
    d = math.sqrt(dx * dx + dz * dz)
    if d < 1e-6:
        return True                                  # on top of the anchor; nothing to aim
    rope = st["rope_len"]
    sbs = _sbs()
    off = sbs.vec3((dx / d) * rope, 0.0, (dz / d) * rope)   # circle point at ship's bearing
    _delete_connection(anchor, ship)
    con = _add_connection(anchor, ship, off, 0.0)
    if con is None:
        return False                                 # the engine refused the beam
    con.offset = st["stiffness"]
    return True


def _tick_lock(src, tgt, st):
    """Harden a winching Grav Lock to rigid once the gap is actually closed.

    Measured against the LIVE separation, not against a ramped rope length: pull_distance
    is not honored as a rest length (the mock ignores it outright, and the engine harness
    read 1500 -> ~165 rather than -> 1500), so a countdown would be a timer pretending to
    be a measurement. Distance is the thing the rule is about, so distance is what it
    reads.
    """
    so = to_object(src)
    to = to_object(tgt)
    if so is None or to is None:
        return True
    if _distance(so, to) > _lock_grab_distance:
        return True                          # still hauling it in on the lagged pull
    st["winch"] = False
    st["stiffness"] = 0.0                    # in reach now - rigid is a grab, not a jump
    st["pull"] = 0.0
    con = _get_connection(src, tgt)
    if con is None:
        con = _add_connection(src, tgt, _to_sbs_vec(st["offset"]), 0.0)
    if con is None:
        return False                         # the engine refused the beam
    con.offset = 0.0
    signal_emit("grav_tether_locked", {"SOURCE_ID": src, "TARGET_ID": tgt})
    return True


def _advance_reel(src, tgt, st):
    new_pull = st["pull"] - st["reel_rate"]
    if new_pull <= 0.0:
        new_pull = 0.0
        st["reel_rate"] = 0.0
    st["pull"] = new_pull
    _delete_connection(src, tgt)
    con = _add_connection(src, tgt, _to_sbs_vec(st["offset"]), new_pull)
    if con is None:
        return False                                 # the engine refused the beam
    con.offset = st["stiffness"]
    if new_pull <= 0.0:
        signal_emit("grav_tether_reeled", {"source": src, "target": tgt})
    return True


#: Key the tow-drag modifiers are registered under, so they can be lifted cleanly.
_DRAG_KEY = "grav_tether_drag"

#: How much of your drive a load of EQUAL mass costs you. A same-mass tow at 0.35 leaves
#: you at 65% throttle and turn - slow enough to be a real decision, not so slow that
#: hauling anything is a punishment.
DRAG_AT_EQUAL_MASS = 0.35

#: Never drag a ship below this fraction of its drive, whatever it has hold of. A ship
#: pinned to 0 is a ship that cannot play; the tug-of-war should make a trip slow and
#: vulnerable, not end it.
DRAG_FLOOR = 0.25


#: Ratio past which a haul is called "overloaded" - the band that means "fetch help".
#: Well above the point drag maxes out, because between the two a crew is merely slow;
#: here the beam's own lag is the thing beating them.
STRAIN_OVERLOAD_RATIO = 10.0


def _drag_amount(ratio):
    """How much drive a load of this mass ratio costs. 0 = free, 0.75 = at the floor."""
    return min(1.0 - DRAG_FLOOR, float(ratio) * DRAG_AT_EQUAL_MASS)


def _drag_floor_ratio():
    """The ratio at which drag stops growing because it has hit :data:`DRAG_FLOOR`."""
    return (1.0 - DRAG_FLOOR) / DRAG_AT_EQUAL_MASS


def grav_tether_strain(source, target):
    """How hard the ships on ``target`` are working, as a word a readout can print.

    ``none`` / ``light`` / ``heavy`` / ``overloaded``. The boundaries are the points where
    the mechanics actually change, not round numbers: ``light`` ends where drag stops
    growing (past there extra mass no longer costs extra drive - only lag and power), and
    ``overloaded`` is where the beam's own sluggishness, not the drive penalty, is what is
    beating the crew.

    A BAND rather than the raw ratio on purpose. The ratio moves whenever anything joins
    or leaves; a band moves about once a haul, which is what lets it drive both an
    edge-triggered signal and a console's repaint key without tearing the panel down.
    """
    ratio = grav_tether_load_ratio(source, target)
    if ratio <= 1.0:
        return "none"
    if ratio < _drag_floor_ratio():
        return "light"
    if ratio < STRAIN_OVERLOAD_RATIO:
        return "heavy"
    return "overloaded"


def _enforce_drag(src, tgt, st):
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
    puller on the next tick with no cache bookkeeping of its own.
    """
    if st.get("swing") or st.get("reversed"):
        return
    _announce_strain(src, tgt, st)
    amount = _drag_amount(grav_tether_load_ratio(src, tgt))
    if amount <= 0.0:
        return
    if st.get("drag") == amount:
        return                              # already applied at this ratio
    try:
        from .modifiers import modifier_add
        modifier_add(src, "impulse_upgrade_coeff", -amount, _DRAG_KEY, replace_if_exists=True)
        modifier_add(src, "turn_upgrade_coeff", -amount, _DRAG_KEY, replace_if_exists=True)
        st["drag"] = amount
    except Exception:
        pass


def _announce_strain(src, tgt, st):
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
    existed and both fired only after the haul had already failed.
    """
    band = grav_tether_strain(src, tgt)
    now = (band, len(grav_tether_pullers_of(tgt)))
    if st.get("strain") == now:
        return
    st["strain"] = now
    if band == "none":
        return                              # not worth saying "this is easy"
    signal_emit("grav_tether_strain", {
        "SOURCE_ID": src, "TARGET_ID": tgt, "STRAIN": band,
        "RATIO": grav_tether_load_ratio(src, tgt),
        "PULLERS": now[1],
    })


def _release_drag(src):
    """Lift the tow drag. Called on release - a ship that let go must get its drive back."""
    try:
        from .modifiers import modifier_remove
        modifier_remove(src, "impulse_upgrade_coeff", _DRAG_KEY)
        modifier_remove(src, "turn_upgrade_coeff", _DRAG_KEY)
    except Exception:
        pass


def grav_tether_tick(t=None):
    """Runs on the TickDispatcher (~7.5/sim-sec in-engine, 6 in the mock - see
    DEFAULT_REEL_RATE) while any tether is live; also directly
    callable (tests). Enforces impulse and advances reels; self-heals dead objects."""
    for key in list(_TETHERS.keys()):
        src, tgt = key
        if not object_exists(src) or not object_exists(tgt):
            grav_tether_release(src, tgt)
            continue
        st = _TETHERS.get(key)
        if st is None:
            continue
        # ONE BAD TETHER MUST NOT TAKE DOWN THE TICK LOOP - and a raise here does not stop
        # at this module. TickTask._update and TickDispatcher.dispatch_tick are both bare,
        # so it aborts the iteration over every OTHER scheduled task that tick and lands in
        # handlerhooks' catch-all, which PAUSES THE SIM and pushes the ErrorPage. Worse,
        # TickTask.start is only refreshed after the callback returns, so "Resume Mission"
        # fires this task on the very next dispatch and raises again: the game is
        # unrecoverable without a restart. Same discipline as DripQueue._run - say what
        # happened, drop the offending tether, keep the loop.
        try:
            if _over_stretched(src, tgt, st):
                grav_tether_release(src, tgt)
                signal_emit("grav_tether_snapped", {"SOURCE_ID": src, "TARGET_ID": tgt})
                continue
            if _enforce_impulse(src, tgt, st):
                continue                       # snapped -> gone this tick
            _enforce_drag(src, tgt, st)        # towing a heavy load costs you speed
            if _spend_tow_energy(src, tgt, st):
                continue                       # ran dry -> released this tick
            if st.get("swing"):
                ok = _tick_swing(src, tgt, st)      # circle-point orbit (holds radius)
            elif st.get("winch"):
                ok = _tick_lock(src, tgt, st)       # lock still closing -> rigid on arrival
            elif st.get("rope"):
                ok = _tick_rope(src, tgt, st)       # trailing tow rope-hold
            elif st.get("reel_rate", 0.0) > 0.0:
                ok = _advance_reel(src, tgt, st)
            else:
                ok = True                           # a static lock needs no upkeep
        except Exception as ex:
            logging.getLogger("mast.runtime").error(
                f"grav_tether: dropping tether {src}->{tgt}: {ex}")
            ok = False
        if not ok:
            grav_tether_release(src, tgt)
    _maybe_stop_tick()
