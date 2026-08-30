"""grav_tether — attach a beam between two space objects to lock / tow / reel a load.

Thin wrappers over the ENGINE-native tractor system (``sim.AddTractorConnection`` /
``DeleteTractorConnection`` / ``GetTractorConnection``) plus the mission-facing behavior
the raw API doesn't provide: the mode presets (lock / tow / reel), a reel ramp, and the
canonical **impulse-only** enforcement.

Confirmed in-engine (Phase 0 spike, GRAV_TETHER_PLAN.md):
  * ``AddTractorConnection(src, tgt, offset_point, pull_distance)`` pulls ``tgt`` toward
    ``src + offset_point``; ``pull_distance`` is a **rope rest-length** (the target
    settles at that distance).
  * the connection's ``.offset`` float is a **stiffness** dial: 0 = rigid lock,
    ~5 = a good taut tow, higher = looser/laggier.
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
DEFAULT_REEL_RATE = 50.0          # rope-length reduced per tick (0.1s) -> ~500 u/s
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
MASS_REVERSE_RATIO = 2.0

#: Above this throttle a target is moving too fast to get hold of - None disables the
#: rule. Off in the library and switched on by the mission, because "can you grab a ship
#: under power" is a game-balance question, not a physics one. Turning it on is what ties
#: the tether to the rest of Weapons: cripple the engines first, THEN grab.
_grab_speed_limit = None

#: Energy the puller spends per tick per unit of towed mass. 0 disables it. Gives
#: Engineering a stake - a long haul competes with shields and weapons for power.
_tow_energy_cost = 0.0

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


def grav_tether_set_anchor_roles(roles):
    """Set the roles that may never be PULLED (comma-separated, or "" to allow all).

    A mission that wants the library default back passes :data:`ANCHOR_ROLES`.
    """
    global _anchor_roles
    _anchor_roles = roles or ""


def grav_tether_is_anchor(obj):
    """Whether this object can only ever be the anchor end of a tether."""
    return bool(_anchor_roles) and has_any_role(to_id(obj), _anchor_roles)


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
    """Charge the puller for holding a load. Returns True if the tether snapped dry.

    Running a ship's reserves to nothing would be a worse mechanic than making the haul
    expensive, so an empty tank BREAKS the beam and drops the load rather than pinning the
    ship at zero energy.
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
    cost = _tow_energy_cost * grav_tether_mass(tgt)
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

    Returns a dict ``{"partner", "mode", "role", "source", "target"}`` - ``role`` is
    ``"source"`` when obj is the puller, ``"target"`` when it is the load. The FIRST
    tether found; a ship holding several is unusual and a one-square readout has room
    for one anyway.
    """
    oid = to_id(obj)
    if oid is None:
        return None
    for (src, tgt), st in _TETHERS.items():
        if oid == src:
            return {"partner": tgt, "mode": st.get("mode"), "role": "source",
                    "source": src, "target": tgt}
        if oid == tgt:
            return {"partner": src, "mode": st.get("mode"), "role": "target",
                    "source": src, "target": tgt}
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
    """Rigid grab: target locked onto the source's offset point (cargo, hangar recovery)."""
    return grav_tether_attach(source, target, offset=offset, stiffness=0.0,
                              pull_distance=0.0, overspeed=overspeed)


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
        con.offset = st["stiffness"]
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


def _drag_amount(ratio):
    """How much drive a load of this mass ratio costs. 0 = free, 0.75 = at the floor."""
    return min(1.0 - DRAG_FLOOR, float(ratio) * DRAG_AT_EQUAL_MASS)


def _enforce_drag(src, tgt, st):
    """Towed mass drops the puller's throttle and turn rate.

    This is what makes big salvage a slow, vulnerable trip home rather than free money.
    Applied as MODIFIERS on the engine's own upgrade coefficients (the same keys the item
    system boosts), so it stacks and expires through machinery that already exists instead
    of fighting the helm for the throttle value every tick.

    A SWING is exempt: the anchor is the source, the fighter is the load, and slowing the
    anchor (usually a rock) means nothing - while slowing the fighter would kill the orbit
    the mode exists for.
    """
    if st.get("swing"):
        return
    amount = _drag_amount(grav_tether_mass_ratio(src, tgt))
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


def _release_drag(src):
    """Lift the tow drag. Called on release - a ship that let go must get its drive back."""
    try:
        from .modifiers import modifier_remove
        modifier_remove(src, "impulse_upgrade_coeff", _DRAG_KEY)
        modifier_remove(src, "turn_upgrade_coeff", _DRAG_KEY)
    except Exception:
        pass


def grav_tether_tick(t=None):
    """Runs on the TickDispatcher (~10 Hz) while any tether is live; also directly
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
            if _enforce_impulse(src, tgt, st):
                continue                       # snapped -> gone this tick
            _enforce_drag(src, tgt, st)        # towing a heavy load costs you speed
            if _spend_tow_energy(src, tgt, st):
                continue                       # ran dry -> released this tick
            if st.get("swing"):
                ok = _tick_swing(src, tgt, st)      # circle-point orbit (holds radius)
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
