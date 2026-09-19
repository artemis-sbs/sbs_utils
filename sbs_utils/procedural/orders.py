"""Who can be given which ORDERS - decided by what the object can actually do.

An order is a MAST objective label under ``objective/orders/`` (the menus and drag
routes build their buttons from them). This module answers the two questions every one
of those menus asks, in ONE place, so the comms chip, the right-click popup and drag can
never disagree:

    orders_available(origin, selected, target)   the order labels that apply
    orders_can_take(origin, selected)            is there any at all?

It used to be one role and one order set, so an allied STATION was offered "Head to
location" and "Attack" - orders it has no engine, and on a stock hull no guns, to carry
out. Now each order label says what it NEEDS, and each object says what it HAS:

    requires: move, weapons        # order label metadata

CAPABILITIES are a small fixed vocabulary:

    move      anything not spawned behav_station / behav_selection
    weapons   a turret, a host with turret mounts, or a MOBILE hull with beams or tubes
              (engine-measured: a behav_station on a stock hull never fires)
    launch    supplied by a provider (the hangar addon knows what is docked where)

Derived defaults, then per-object overrides (`orders_caps_set`), and the ``no_orders``
role still blocks everything.

`give_orders_type` on the object NARROWS the set by label-type prefix, so a ship class
can have its own order set (``objective/orders/escort``) without a new capability.

STANCE (weapons free / hold fire) is stored here too, because both the turret brain in
this library and the chase brains in a mission read it.
"""
from .inventory import get_inventory_value, set_inventory_value
from .query import to_id, to_object, object_exists
from .roles import has_role
from .ship_data import get_ship_data_for


#: Every order label's type starts with this.
ORDERS_TYPE = "objective/orders/"

#: A mission marks a story ship with this and it takes no orders at all.
ORDERS_BLOCK_ROLE = "no_orders"

#: The historic "you may order this" role, from the defender prefab and a captured prize.
ORDERS_DEFENDER_ROLE = "prefab_npc_defender"

#: The capability vocabulary. Anything else in a `requires:` is a typo and never matches.
ORDERS_CAPS = ("move", "weapons", "launch")

#: Marker objects (procedural/markers.py marker_object) - a `valid_for: marker` target.
ORDERS_MARKER_ROLE = "marker"

ORDERS_STANCE_FREE = "free"
ORDERS_STANCE_HOLD = "hold"

_CAPS_ADD = "orders_caps_add"
_CAPS_REMOVE = "orders_caps_remove"
_STANCE = "orders_stance"

#: Behaviors that never steer. behav_selection is map furniture.
_STILL_BEHAVIORS = ("behav_station", "behav_selection")

# fn(obj_id) -> iterable of capability names. Registered by addons (the hangar supplies
# `launch`); module-level, but it holds FUNCTIONS registered at import, not per-mission
# state, so it is deliberately not on the reset ledger.
_providers = []


def _split(value):
    """`"move, weapons"` / `["move"]` / None -> a set of stripped lowercase names."""
    if value is None:
        return set()
    if isinstance(value, str):
        value = value.split(",")
    return {str(v).strip().lower() for v in value if str(v).strip()}


def orders_caps_provider(fn):
    """Register `fn(obj_id) -> iterable of capability names`, added to every object's
    derived set. How an addon contributes a capability this library cannot see (what
    craft are docked at a station). Idempotent. Returns `fn` so it works as a decorator.
    """
    # Keyed by NAME, not identity: cosmos_dev reuses one interpreter across missions and
    # re-imports an addon's .py, so the "same" provider arrives as a new function object
    # each run - by identity it would register once per run and add its caps N times.
    key = (getattr(fn, "__module__", None), getattr(fn, "__qualname__", None))
    for i, have in enumerate(_providers):
        if (getattr(have, "__module__", None), getattr(have, "__qualname__", None)) == key:
            _providers[i] = fn
            return fn
    _providers.append(fn)
    return fn


def _orders_is_mobile(obj):
    behave = getattr(obj, "behave_id", None)
    if behave is not None:
        return behave not in _STILL_BEHAVIORS
    # Spawned before behave_id was recorded (or not by the library): fall back to what
    # the roles say. Terrain never moves under its own power.
    if getattr(obj, "is_terrain", False):
        return False
    return not has_role(obj.id, "station")


def _orders_hull_armed(obj):
    """Does the hull carry beams or torpedo tubes, per ship data?"""
    key = getattr(obj, "_ship_data_key", None) or getattr(obj, "art_id", None)
    entry = get_ship_data_for(key) if key else None
    if not entry:
        return False
    if (entry.get("tubecount") or 0) > 0:
        return True
    hps = entry.get("hull_port_sets")
    if isinstance(hps, dict):
        for name, ports in hps.items():
            if isinstance(name, str) and name.startswith("beam") and ports:
                return True
    return False


def orders_mounted_turrets(obj):
    """The turret mounts welded to a host - where a STATION's weapon orders go."""
    from .mount import mount_list
    from .turret import turret_is
    oid = to_id(obj)
    if oid is None:
        return []
    return [m for m in mount_list(oid) if turret_is(m)]


def orders_caps(obj):
    """The set of capabilities an object has: derived, then overridden.

    Returns an empty set for a missing object.
    """
    from .turret import turret_is
    so = to_object(obj)
    if so is None:
        return set()
    oid = so.id
    caps = set()
    mobile = _orders_is_mobile(so)
    if mobile:
        caps.add("move")
    if turret_is(oid) or orders_mounted_turrets(oid) or (mobile and _orders_hull_armed(so)):
        caps.add("weapons")
    for fn in list(_providers):
        try:
            caps |= _split(fn(oid))
        except Exception:                               # noqa: BLE001
            pass                                        # a broken provider adds nothing
    caps |= _split(get_inventory_value(oid, _CAPS_ADD, None))
    caps -= _split(get_inventory_value(oid, _CAPS_REMOVE, None))
    return caps


def orders_caps_set(obj, add=None, remove=None):
    """Override an object's capabilities. `add`/`remove` are a name, a comma string or a
    list; each call REPLACES the previous override of that kind. Pass "" to clear one.

        orders_caps_set(freighter_id, remove="weapons")   # armed, but will not fight
        orders_caps_set(platform_id, add="weapons")       # a hull this library misreads
    """
    oid = to_id(obj)
    if oid is None:
        return None
    if add is not None:
        set_inventory_value(oid, _CAPS_ADD, sorted(_split(add)))
    if remove is not None:
        set_inventory_value(oid, _CAPS_REMOVE, sorted(_split(remove)))
    return orders_caps(oid)


def _orders_same_or_allied(a, b):
    from .sides import side_are_allies, to_side_id
    try:
        sa = to_side_id(a, warn=False)
        if sa is not None and sa == to_side_id(b, warn=False):
            return True
        return bool(side_are_allies(a, b))
    except Exception:                                   # noqa: BLE001
        return False


def orders_may_command(origin, selected):
    """May `origin` give orders to `selected` AT ALL - before asking what it can do?

    Not `no_orders`; then the defender role, or an NPC on the origin's own side or an
    allied one.
    """
    sid = to_id(selected)
    if not sid or not object_exists(sid):
        return False
    if has_role(sid, ORDERS_BLOCK_ROLE):
        return False
    if has_role(sid, ORDERS_DEFENDER_ROLE):
        return True
    if not has_role(sid, "__npc__"):
        return False
    return _orders_same_or_allied(origin, sid)


def orders_set_prefix(obj):
    """The label-type prefix an object's orders come from: its `give_orders_type`, or
    every order."""
    oid = to_id(obj)
    kind = get_inventory_value(oid, "give_orders_type", None) if oid else None
    return kind or ORDERS_TYPE


def _orders_labels(prefix, labels=None):
    if labels is not None:
        return list(labels)
    from .execution import labels_get_type
    return labels_get_type(prefix)


def _label_type(label):
    return label.get_inventory_value("type", None) or getattr(label, "path", None) or getattr(label, "name", "")


def _orders_target_fits(valid_for, selected, target, at_point=False):
    """Does `valid_for` (a name or a comma list) accept this target?

    self     no target, or the selected object itself
    point    a spot in space with no object (`at_point`)
    allies   own side or allied with the SELECTED object
    hostile  anything else that is a ship
    marker   a marker object
    any      any target (a point, an object, a marker - but not self)
    """
    kinds = _split(valid_for) or {"any"}
    tid = to_id(target) if target is not None else None
    if not tid and at_point:
        return bool(kinds & {"point", "any"})
    if not tid or tid == to_id(selected):
        return "self" in kinds
    if "any" in kinds:
        return True
    if has_role(tid, ORDERS_MARKER_ROLE):
        return "marker" in kinds
    if _orders_same_or_allied(selected, tid):
        return "allies" in kinds
    return "hostile" in kinds


def orders_available(origin, selected, target=None, labels=None, at_point=False):
    """The order labels `origin` may give `selected`, aimed at `target`.

    `target` None (or `selected` itself) asks for the orders it gives ITSELF - full stop,
    hold fire - unless `at_point` says it is an empty spot in space, which only `point`
    and `any` orders accept. `labels` overrides the story lookup, for tests.

    Returns [] when the origin may not command it at all.
    """
    if not orders_may_command(origin, selected):
        return []
    caps = orders_caps(selected)
    prefix = orders_set_prefix(selected)
    out = []
    for label in _orders_labels(prefix, labels):
        if not str(_label_type(label)).startswith(prefix):
            continue
        if not _split(label.get_inventory_value("requires", None)) <= caps:
            continue
        if not _orders_target_fits(label.get_inventory_value("valid_for", "any"), selected, target, at_point):
            continue
        out.append(label)
    return out


def orders_can_take(origin, selected, labels=None):
    """Does `selected` have ANY order `origin` could give it? What the "Can order" chip,
    the comms enable route and drag all ask. Ignores the target - any target will do.
    """
    if not orders_may_command(origin, selected):
        return False
    caps = orders_caps(selected)
    prefix = orders_set_prefix(selected)
    for label in _orders_labels(prefix, labels):
        if not str(_label_type(label)).startswith(prefix):
            continue
        if _split(label.get_inventory_value("requires", None)) <= caps:
            return True
    return False


def orders_stance(obj):
    """"free" (the default) or "hold"."""
    oid = to_id(obj)
    if oid is None:
        return ORDERS_STANCE_FREE
    return get_inventory_value(oid, _STANCE, ORDERS_STANCE_FREE) or ORDERS_STANCE_FREE


def orders_stance_set(obj, stance):
    """Weapons free or hold fire. A host passes it on to its turret mounts, since they
    are what does its shooting. Returns the stance set, or None for a bad value."""
    stance = str(stance or "").strip().lower()
    if stance not in (ORDERS_STANCE_FREE, ORDERS_STANCE_HOLD):
        return None
    oid = to_id(obj)
    if oid is None:
        return None
    set_inventory_value(oid, _STANCE, stance)
    for m in orders_mounted_turrets(oid):
        set_inventory_value(m, _STANCE, stance)
    return stance


def orders_holding_fire(obj):
    """True while an object is ordered to hold fire."""
    return orders_stance(obj) == ORDERS_STANCE_HOLD
