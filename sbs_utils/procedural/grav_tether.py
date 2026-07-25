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
"""

import math

from ..helpers import FrameContext
from ..tickdispatcher import TickDispatcher
from .query import to_id, to_object, object_exists, get_data_set_value
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

# (src_id, tgt_id) -> state we must keep ourselves (the connection object exposes only
# .offset, not the offset_point / pull_distance we need to re-attach for a reel).
_TETHERS = {}
_tick_task = None


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
    if src is None or tgt is None or src == 0 or tgt == 0:
        return None
    sim = _sim()
    sim.DeleteTractorConnection(src, tgt)
    con = sim.AddTractorConnection(src, tgt, _to_sbs_vec(offset), float(pull_distance))
    con.offset = float(stiffness)
    _TETHERS[(src, tgt)] = {
        "offset": offset,
        "stiffness": float(stiffness),
        "pull": float(pull_distance),
        "overspeed": overspeed if overspeed is not None else _default_overspeed,
        "reel_rate": 0.0,
    }
    _ensure_tick()
    return con


def grav_tether_release(source, target):
    """Break a single tether (source no longer pulls target). Safe if none exists."""
    src = to_id(source)
    tgt = to_id(target)
    if src is None or tgt is None:
        return
    _sim().DeleteTractorConnection(src, tgt)
    _TETHERS.pop((src, tgt), None)
    _maybe_stop_tick()


def grav_tether_release_all(source):
    """Break every tether where ``source`` is the puller."""
    src = to_id(source)
    for key in [k for k in _TETHERS if k[0] == src]:
        _sim().DeleteTractorConnection(key[0], key[1])
        _TETHERS.pop(key, None)
    _maybe_stop_tick()


def grav_tether_get(source, target):
    """Return the live tractor_connection for the pair, or None."""
    src = to_id(source)
    tgt = to_id(target)
    if src is None or tgt is None:
        return _sim().GetTractorConnection(src or 0, tgt or 0)
    return _sim().GetTractorConnection(src, tgt)


def grav_tether_clear_all():
    """Drop all tethers (fresh mission / test reset)."""
    _sim().ClearTractorConnections()
    _TETHERS.clear()
    _maybe_stop_tick()


# --- mode presets ---------------------------------------------------------------

def grav_tether_lock(source, target, offset=None, overspeed=None):
    """Rigid grab: target locked onto the source's offset point (cargo, hangar recovery)."""
    return grav_tether_attach(source, target, offset=offset, stiffness=0.0,
                              pull_distance=0.0, overspeed=overspeed)


def grav_tether_tow(source, target, distance, offset=None,
                    stiffness=DEFAULT_TOW_STIFFNESS, overspeed=None):
    """Springy trailing tow: hold the load ``distance`` behind (rope rest-length)."""
    return grav_tether_attach(source, target, offset=offset, stiffness=stiffness,
                              pull_distance=float(distance), overspeed=overspeed)


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


def _advance_reel(src, tgt, st):
    new_pull = st["pull"] - st["reel_rate"]
    if new_pull <= 0.0:
        new_pull = 0.0
        st["reel_rate"] = 0.0
    st["pull"] = new_pull
    sim = _sim()
    sim.DeleteTractorConnection(src, tgt)
    con = sim.AddTractorConnection(src, tgt, _to_sbs_vec(st["offset"]), new_pull)
    con.offset = st["stiffness"]
    if new_pull <= 0.0:
        signal_emit("grav_tether_reeled", {"source": src, "target": tgt})


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
        if _enforce_impulse(src, tgt, st):
            continue                       # snapped -> gone this tick
        if st["reel_rate"] > 0.0:
            _advance_reel(src, tgt, st)
    _maybe_stop_tick()
