"""Turrets: emplacements that acquire a target and fire, and never move.

A turret is an ACTIVE space object (``npc_spawn``) whose entire behavior is "find
something worth shooting, point the weapons at it, hold still". The engine's beams do
the actual firing - there is no ``sbs.fire_beam`` - so all this module ever writes is
``target_id``, via :func:`target_shoot`. That one fact is what makes a deployable tower
and a turret bolted to a ship's hull the same thing: they differ only in where their
POSITION comes from (see :mod:`sbs_utils.procedural.mount`), never in how they fight.

ENGINE-MEASURED (1.3.5, ``LM_TestRange/maps/test_turret_probe.mast``) - three findings
shape everything here:

* ``target_shoot()`` ALONE is enough. Writing only ``target_id``, with no throttle and
  no destination, made an NPC fire (13 hits / 65 damage). Nothing else needs writing,
  and writing more would make the turret move.
* A ``behav_station`` fires ONLY from a hull declared through ``ship_data_merge_mod``.
  Both stock hulls tested stayed silent with the identical call; both add-on hulls fired.
  **A turret must therefore spawn art the mission ships itself** - see
  ``LegendaryMissions/turrets/shipData_turrets.yaml``.
* ``beamRange`` / ``beamCount`` / ``beamDamage`` are MOCK INVENTIONS. They read ``None``
  on stock engine hulls, because beam stats live in the engine's ship table and not in
  the object's data_set. So range CANNOT be read off the object or tuned per-object -
  :func:`turret_range` returns what the author configured, and each turret variant that
  needs different beams needs its own hull entry.

**Every module-level function here is prefixed**, private ones included. MAST imports a
module's functions into ONE flat, mission-wide namespace with no underscore filtering, so
a helper named ``_key`` turns any script's ``_key = ...`` into "Variable assignment to a
keyword" - which desyncs the compiler and empties the whole story.

**No module-level state.** Every per-turret value lives in that turret's own inventory,
so ``Agent._remove`` purges it on delete: config cannot outlive its object, a recycled
id cannot inherit stale settings, and there is nothing to register with
``register_reset_state``.
"""

from ..helpers import FrameContext
from .inventory import get_inventory_value, set_inventory_value
from .query import object_exists, to_id, to_object
from .roles import add_role, has_role, role, role_matches
from .sides import side_hostile_ships
from .space_objects import (broad_test_around, clear_target, closest,
                            closest_in_front, target_shoot)


#: Role every turret carries, so turrets can find each other and refuse to duel.
TURRET_ROLE = "__TURRET__"

#: Fallback range when the author configures none. Beam stats are not readable from the
#: object (see the module docstring), so there is nothing better to fall back TO - this
#: is a number, not a measurement, and an author who cares should pass ``range=``.
TURRET_DEFAULT_RANGE = 3000.0

#: How long a turret sticks with a target before it will consider switching.
TURRET_HOLD_SECONDS = 3.0

#: Keep firing out to ``range * slack`` before dropping a target. Without the hysteresis
#: a target hovering at exactly max range is acquired and dropped on alternate scans.
TURRET_HOLD_SLACK = 1.15

#: Default of what a turret considers worth shooting, as a role expression
#: (see :func:`sbs_utils.procedural.roles.role_matches`).
TURRET_DEFAULT_TARGETS = "__player__|ship|shuttle|fighter|bomber|station|cockpit"

def _turret_key(name):
    return "turret:" + name


def _turret_now():
    ctx = FrameContext.context
    return 0.0 if ctx is None else (FrameContext.sim_seconds or 0.0)


def turret_make(id_or_obj, range=None, arc=None, targets=None, priority="closest",
                hold_seconds=None, hold_slack=None):
    """Turn an existing space object into a turret.

    Does NOT spawn anything and does NOT make it stand still - a turret holds position
    because of the behavior it was spawned with (``behav_station``) or because a mount
    is placing it, not because of anything written here.

    Args:
        id_or_obj (Agent | int): The object to arm.
        range (float, optional): Engagement range. Defaults to
            :data:`TURRET_DEFAULT_RANGE`. Note this gates ACQUISITION only - what the
            beams can actually reach comes from the hull's shipData and is not readable.
        arc (float, optional): Firing arc in degrees, centered on the turret's heading.
            Defaults to None, meaning 360 (no arc test). Every stock station beam is
            already 360, so an arc is rarely what you want.
        targets (str, optional): Role EXPRESSION of what to shoot. Defaults to
            :data:`TURRET_DEFAULT_TARGETS`.
        priority (str, optional): ``"closest"`` (default) or ``"weakest"``.
        hold_seconds (float, optional): Target persistence. Defaults to
            :data:`TURRET_HOLD_SECONDS`.
        hold_slack (float, optional): Range hysteresis multiplier. Defaults to
            :data:`TURRET_HOLD_SLACK`.

    Returns:
        int | None: The turret's id, or None if the object does not exist.
    """
    tid = to_id(id_or_obj)
    if tid is None or not object_exists(tid):
        return None
    add_role(tid, TURRET_ROLE)
    add_role(tid, "turret")
    set_inventory_value(tid, _turret_key("range"),
                        float(range) if range else TURRET_DEFAULT_RANGE)
    set_inventory_value(tid, _turret_key("arc"), float(arc) if arc else 0.0)
    set_inventory_value(tid, _turret_key("targets"), targets or TURRET_DEFAULT_TARGETS)
    set_inventory_value(tid, _turret_key("priority"), priority or "closest")
    set_inventory_value(tid, _turret_key("hold_seconds"),
                        TURRET_HOLD_SECONDS if hold_seconds is None else float(hold_seconds))
    set_inventory_value(tid, _turret_key("hold_slack"),
                        TURRET_HOLD_SLACK if hold_slack is None else float(hold_slack))
    return tid


def turret_is(id_or_obj):
    """Whether an object is a turret."""
    return has_role(id_or_obj, TURRET_ROLE)


def turret_all():
    """Every live turret, as a set of ids."""
    return role(TURRET_ROLE)


def turret_config(id_or_obj, key, default=None):
    """Read one configured value (``range``, ``arc``, ``targets``, ...)."""
    return get_inventory_value(id_or_obj, _turret_key(key), default)


def turret_set(id_or_obj, key, value):
    """Change one configured value on a live turret."""
    set_inventory_value(id_or_obj, _turret_key(key), value)
    return value


def turret_range(id_or_obj):
    """The turret's configured acquisition range.

    Reads what the author set, NOT the hull's beams: the engine keeps beam stats in its
    ship table, so ``beamRange`` on the object reads None (it exists only in the mock and
    on add-on hulls, where sbs_utils wrote it). A turret whose configured range disagrees
    with its hull will acquire targets it cannot hit - keep them in step in shipData.
    """
    return turret_config(id_or_obj, "range", TURRET_DEFAULT_RANGE) or TURRET_DEFAULT_RANGE


def turret_target(id_or_obj):
    """The turret's current target id, or None."""
    t = turret_config(id_or_obj, "target")
    return t if t else None


def turret_designate(id_or_obj, target_id):
    """Order a turret to shoot a specific thing (a player or GM command).

    A designated target beats acquisition entirely and is never re-evaluated against
    closer candidates - the point of an order is that it is not second-guessed. It is
    still dropped when the target dies or leaves ``range * hold_slack``. Pass None to
    return the turret to free-fire.
    """
    tid = to_id(id_or_obj)
    if tid is None:
        return None
    did = to_id(target_id) if target_id is not None else None
    set_inventory_value(tid, _turret_key("designated"), did or 0)
    return did


def turret_engage(id_or_obj, target_id=None):
    """Point the weapons at a target and NOTHING else.

    This is the whole firing mechanism: the engine's beams fire on their own at whatever
    ``target_id`` holds. Deliberately does not touch ``throttle`` or ``target_pos_*`` -
    that is the difference between :func:`target_shoot` and :func:`target`, and it is
    what keeps a turret from wandering off after its victim.

    Returns:
        int | None: The engaged target id, or None.
    """
    tid = to_id(id_or_obj)
    did = to_id(target_id) if target_id is not None else None
    if tid is None:
        return None
    if did is None or not object_exists(did):
        return None
    target_shoot(tid, did)
    set_inventory_value(tid, _turret_key("target"), did)
    set_inventory_value(tid, _turret_key("hold_until"),
                        _turret_now() + (turret_config(tid, "hold_seconds", TURRET_HOLD_SECONDS) or 0.0))
    return did


def turret_disengage(id_or_obj):
    """Stop shooting and forget the current target."""
    tid = to_id(id_or_obj)
    if tid is None:
        return None
    if object_exists(tid):
        clear_target(tid)
    set_inventory_value(tid, _turret_key("target"), 0)
    set_inventory_value(tid, _turret_key("hold_until"), 0.0)
    return tid


def turret_in_range(id_or_obj, target_id, slack=True):
    """Whether a target is close enough to keep or take, honoring the hysteresis."""
    tid, did = to_id(id_or_obj), to_id(target_id)
    if tid is None or did is None or not object_exists(did) or not object_exists(tid):
        return False
    rng = turret_range(tid)
    if slack:
        rng *= (turret_config(tid, "hold_slack", TURRET_HOLD_SLACK) or 1.0)
    ctx = FrameContext.context
    if ctx is None:
        return False
    try:
        return ctx.sbs.distance_id(tid, did) <= rng
    except Exception:
        return False


def turret_candidates(id_or_obj):
    """Everything this turret is willing to shoot, before distance and arc.

    Diplomacy decides allegiance via :func:`side_hostile_ships`, which already drops
    wrecks, surrendered ships, and any side that has ceasefired - so a turret stops
    firing the moment a truce is signed, with no tag to keep in sync. Turrets are then
    removed from their own candidate set: an emplacement duelling another emplacement
    while the ships it was built to stop fly past is never what an author wanted.
    """
    tid = to_id(id_or_obj)
    if tid is None:
        return set()
    return side_hostile_ships(tid) - turret_all() - {tid}


def turret_acquire(id_or_obj):
    """Decide what this turret should be shooting, in priority order.

    1. A DESIGNATED target, while it lives and is in range. Never re-evaluated.
    2. The CURRENT target, until ``hold_seconds`` expires, while it is inside
       ``range * hold_slack``. A marginally closer candidate does not steal it - this is
       the entire anti-thrash rule, and without it a turret between two enemies flips
       every scan and effectively never fires.
    3. Otherwise, scan: nearest (or weakest) hostile inside range that matches the
       ``targets`` role expression.

    Returns:
        int | None: The id to engage, or None if there is nothing to shoot.
    """
    tid = to_id(id_or_obj)
    if tid is None or not object_exists(tid):
        return None

    designated = turret_config(tid, "designated", 0)
    if designated and turret_in_range(tid, designated):
        return designated

    current = turret_target(tid)
    if current and turret_in_range(tid, current):
        if _turret_now() < (turret_config(tid, "hold_until", 0.0) or 0.0):
            return current

    expr = turret_config(tid, "targets", TURRET_DEFAULT_TARGETS)
    cands = turret_candidates(tid)
    if not cands:
        return None

    def _ok(agent):
        return agent is not None and role_matches(agent, expr)

    rng = turret_range(tid)
    arc = turret_config(tid, "arc", 0.0) or 0.0

    # Do the broad phase ourselves, for two reasons that both bite silently:
    #  * broad_test_around takes a box WIDTH, so closest(max_dist=rng) narrows to
    #    +-rng/2 and misses everything past half range. (LM brains pass 2*rng for
    #    exactly this reason.) Passing max_dist=None below stops closest redoing it.
    #  * closest() does `the_set &= ...`, which mutates the set it is HANDED - so it
    #    is given a copy, or _turret_weakest below would only see what closest left behind.
    near = cands & broad_test_around(tid, 2 * rng, 2 * rng, 0xFFFF)
    if not near:
        return None
    if arc and arc < 360:
        found = closest_in_front(tid, set(near), None, arc / 2.0, _ok)
    else:
        found = closest(tid, set(near), None, _ok)
    if found is None or found.distance > rng:
        return None
    # closest() returns CloseData (.id / .distance), not an id or an object.
    best = found.id
    if (turret_config(tid, "priority", "closest") or "closest") == "weakest":
        best = _turret_weakest(tid, near, rng, expr) or best
    return best if best else None


def _turret_weakest(tid, cands, rng, expr):
    """Lowest remaining shields among in-range matches - finish something off rather
    than spreading damage. Falls back to None so the caller keeps the nearest."""
    best, best_shield = None, None
    ctx = FrameContext.context
    if ctx is None:
        return None
    for cid in cands:
        agent = to_object(cid)
        if agent is None or not role_matches(agent, expr):
            continue
        try:
            if ctx.sbs.distance_id(tid, cid) > rng:
                continue
            shield = agent.data_set.get("shield_val", 0) or 0.0
        except Exception:
            continue
        if best_shield is None or shield < best_shield:
            best, best_shield = cid, shield
    return best


def turret_tick(id_or_obj):
    """Acquire and engage in one call - the whole turret loop.

    The brain label is a thin wrapper over this so the policy lives in exactly one place
    and Python callers do not have to reimplement it.

    Returns:
        int | None: The engaged target, or None if it stood down.
    """
    tid = to_id(id_or_obj)
    if tid is None or not object_exists(tid):
        return None
    found = turret_acquire(tid)
    if found is None:
        if turret_target(tid):
            turret_disengage(tid)
        return None
    return turret_engage(tid, found)
