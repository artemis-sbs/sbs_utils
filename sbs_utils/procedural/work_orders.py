"""Work orders: what a damage-control team has been told to go and do.

The model was, and still is, a LINK - ``link(dc, "work-order", node)``. This module
does not replace that; it is a superset layered on the same link, because missions
outside this repo already file orders with a bare ``link()`` and must keep working.

    An order is a property of the TARGET; the link is the assignment.

A node has at most one order - a KIND and a PRIORITY, kept in the node's own
inventory. Any number of teams can be linked to it. A target that has links but no
record gets a **synthesized** one, which is exactly what a bare ``link()`` produces,
so an old mission's orders read back as ordinary orders with sensible defaults.

There is deliberately no ``__work_order__`` role. It would make "every node with an
order" a cheap set intersection, but a bare ``link()`` would not carry it, so the
query would silently under-report precisely the missions this design exists to
protect. ``has_link(WORK_ORDER_LINK)`` already gives the sources for free.

**Orders are purged as they are read.** They never were before: ``Agent._remove``
clears the role and link REGISTRIES when a node dies, but not the entries in another
agent's own link set, so a team's link to a deleted node survived forever and the
count on the console was permanently wrong. ``work_orders_for`` walks one team's link
set - normally nought to three ids - and drops what is no longer real, and every
caller already runs per damcon. No timer, no module-level state, nothing to register
with the reset ledger.
"""
from .query import to_id, to_object, to_set
from .roles import role, has_role, add_role, remove_role
from .links import link, unlink, linked_to, has_link, has_link_to
from .inventory import get_inventory_value, set_inventory_value
from .grid import grid_objects, grid_closest, grid_valid_blob, grid_object_valid
from .internal_damage import grid_node_state

WORK_ORDER_LINK = "work-order"

KIND_REPAIR = "repair"
KIND_MAINTAIN = "maintain"

# A marker role saying "a team has been SENT here to tune this", carried only while a
# maintenance order is open. The brain needs something to match on and it cannot use
# `__worn__`: the whole point is that a NOMINAL node can be tuned, and a nominal node
# is not worn.
#
# A marker, never the order store - `work_order_add` is its only writer, so a bare
# `link()` from an older mission does not carry it. That is exactly right, because a
# bare link has always meant a repair.
MAINTENANCE_ROLE = "__maintenance__"

# A priority is a plain number so a mission can invent its own; these are the rungs
# the comms buttons and `work_order_bump` step between.
PRIORITY_LOW = 10
PRIORITY_NORMAL = 50
PRIORITY_HIGH = 80
PRIORITY_CRITICAL = 100
PRIORITY_STEPS = (PRIORITY_LOW, PRIORITY_NORMAL, PRIORITY_HIGH, PRIORITY_CRITICAL)

# The target node's inventory key holding {"kind": ..., "priority": ...}.
_ORDER_KEY = "work_order"


def work_order_kind_wanted(id_or_obj):
    """What kind of order this node would ACCEPT, or None if there is nothing to gain.

    Note "accept", not "need". A **nominal** node takes a maintenance order too -
    tuning it is how a crew earns the tuned tier at all. Gating this on `__worn__`
    made cyan reachable only by neglecting a system and then fixing it, which is the
    exact opposite of rewarding a well-run ship.

    Only an already-tuned node answers None: there is genuinely nothing left to do.

    Args:
        id_or_obj: a grid node.

    Returns:
        str | None: KIND_REPAIR for a damaged node, KIND_MAINTAIN for a worn or
        nominal one, None for one already at spec.
    """
    node_id = to_id(id_or_obj)
    state = grid_node_state(node_id)
    if state == "damaged":
        return KIND_REPAIR
    if state == "tuned":
        return None
    return KIND_MAINTAIN


def _default_kind(node_id):
    """The kind an order on this node defaults to.

    Falls back to repair rather than None: a bare `link()` from an older mission was
    always a repair order, and a node that has since been fixed still has to read
    back as the order somebody filed.
    """
    return work_order_kind_wanted(node_id) or KIND_REPAIR


def _default_priority(kind):
    """Repairs outrank maintenance by default; both are movable."""
    return PRIORITY_LOW if kind == KIND_MAINTAIN else PRIORITY_NORMAL


def work_order_get(id_or_obj, ensure=False):
    """The order on a node, synthesizing one for a bare ``link()``.

    Args:
        id_or_obj: a grid node.
        ensure (bool, optional): persist a synthesized record. Defaults to False,
            which keeps this a pure read.

    Returns:
        dict | None: ``{"kind": ..., "priority": ...}``, or None when nothing is
        assigned to this node at all.
    """
    node_id = to_id(id_or_obj)
    if node_id is None:
        return None
    order = get_inventory_value(node_id, _ORDER_KEY, None)
    if order is not None:
        return order
    # No record. It is still an order if somebody is linked to it - that IS the old
    # model, and it is the whole back-compat story.
    if not work_order_workers(node_id):
        return None
    kind = _default_kind(node_id)
    order = {"kind": kind, "priority": _default_priority(kind)}
    if ensure:
        set_inventory_value(node_id, _ORDER_KEY, order)
    return order


def work_order_kind(id_or_obj):
    """The order's kind, or None when the node has no order."""
    order = work_order_get(id_or_obj)
    return None if order is None else order.get("kind")


def work_order_priority(id_or_obj):
    """The order's priority, or 0 when the node has no order."""
    order = work_order_get(id_or_obj)
    return 0 if order is None else order.get("priority", PRIORITY_NORMAL)


def work_order_add(worker, id_or_obj, kind=None, priority=None):
    """Send a team to a node, filing (or refreshing) the order on it.

    Accepts sets on either side, exactly as ``link`` does.

    Args:
        worker: the damcon team (or a set of them).
        id_or_obj: the target node (or a set of them).
        kind (str, optional): KIND_REPAIR / KIND_MAINTAIN. Defaults to what the node
            currently needs.
        priority (int, optional): defaults to NORMAL for a repair, LOW for
            maintenance. An existing priority is KEPT unless one is passed - a
            second team joining a job must not quietly demote it.

    Returns:
        dict | None: the order on the last target touched.
    """
    link(worker, WORK_ORDER_LINK, id_or_obj)
    order = None
    for node_id in (to_id(x) for x in to_set(id_or_obj)):
        if node_id is None:
            continue
        existing = get_inventory_value(node_id, _ORDER_KEY, None) or {}
        this_kind = kind or existing.get("kind") or _default_kind(node_id)
        this_priority = (priority if priority is not None
                         else existing.get("priority", _default_priority(this_kind)))
        order = {"kind": this_kind, "priority": this_priority}
        set_inventory_value(node_id, _ORDER_KEY, order)
        if this_kind == KIND_MAINTAIN:
            add_role(node_id, MAINTENANCE_ROLE)
        else:
            remove_role(node_id, MAINTENANCE_ROLE)
    return order


def work_order_cancel(worker, id_or_obj):
    """Take one team off a node. The order survives while anyone is still on it."""
    unlink(worker, WORK_ORDER_LINK, id_or_obj)
    for node_id in (to_id(x) for x in to_set(id_or_obj)):
        if node_id is not None and not work_order_workers(node_id):
            set_inventory_value(node_id, _ORDER_KEY, None)
            remove_role(node_id, MAINTENANCE_ROLE)


def work_order_cancel_all(id_or_obj):
    """Close a node's order for EVERY team on it.

    What repair does. Dropping only the repairer's own link left a second team
    walking to a room that was already fixed - the `role("__damaged__")` filter
    stopped them acting on it, silently, but the link itself never went away.
    """
    for node_id in (to_id(x) for x in to_set(id_or_obj)):
        if node_id is None:
            continue
        for worker_id in list(work_order_workers(node_id)):
            unlink(worker_id, WORK_ORDER_LINK, node_id)
        set_inventory_value(node_id, _ORDER_KEY, None)
        remove_role(node_id, MAINTENANCE_ROLE)


def work_order_workers(id_or_obj):
    """Every team currently assigned to this node.

    Args:
        id_or_obj: a grid node.

    Returns:
        set[int]: the damcon ids linked to it.
    """
    node_id = to_id(id_or_obj)
    if node_id is None:
        return set()
    return {w for w in has_link(WORK_ORDER_LINK)
            if has_link_to(w, WORK_ORDER_LINK, node_id)}


def work_order_set_priority(id_or_obj, priority):
    """Set an order's priority. No-op on a node with no order."""
    node_id = to_id(id_or_obj)
    order = work_order_get(node_id)
    if order is None:
        return None
    order = {"kind": order.get("kind", KIND_REPAIR), "priority": priority}
    set_inventory_value(node_id, _ORDER_KEY, order)
    return order


def work_order_bump(id_or_obj, step=1):
    """Move an order along PRIORITY_STEPS, clamped at both ends.

    Args:
        id_or_obj: a grid node.
        step (int, optional): rungs to move; negative lowers. Defaults to 1.

    Returns:
        int | None: the new priority, or None if the node has no order.
    """
    current = work_order_priority(id_or_obj)
    if current == 0:
        return None
    # The nearest rung to where we are, so an order carrying a mission's own custom
    # number still moves sensibly instead of snapping to LOW.
    index = min(range(len(PRIORITY_STEPS)),
                key=lambda i: abs(PRIORITY_STEPS[i] - current))
    index = max(0, min(len(PRIORITY_STEPS) - 1, index + step))
    order = work_order_set_priority(id_or_obj, PRIORITY_STEPS[index])
    return None if order is None else order["priority"]


def work_order_is_satisfied(id_or_obj):
    """Whether the work this order asked for has been done.

    A repair is satisfied when the node is no longer damaged. Maintenance is
    satisfied when the node is **tuned** - not merely when it stopped being worn.
    Reading it as "no longer `__worn__`" made an order on a nominal node instantly
    complete, so it was purged on the first read and a healthy system could never be
    tuned at all.

    A node with no order is trivially satisfied.
    """
    node_id = to_id(id_or_obj)
    kind = work_order_kind(node_id)
    if kind is None:
        return True
    if kind == KIND_MAINTAIN:
        return grid_node_state(node_id) == "tuned"
    return not has_role(node_id, "__damaged__")


def work_orders_for(worker, purge=True):
    """This team's live work orders, dropping any that are no longer real.

    THE purge point. Six ways an order stops being real, every one of which used to
    leave a link behind forever:

    * the target was deleted (`Agent._remove` clears the registries, not this set)
    * the target's host is gone or exploding
    * the target is not on the worker's ship any more - a grid rebuild replaces
      every id, so an old id can even collide with a new node
    * somebody else already did the work
    * the worker's ship exploded
    * the worker itself is dead

    Args:
        worker: the damcon team.
        purge (bool, optional): actually unlink what is dropped. Defaults to True;
            pass False for a read that must not write (a signature, a probe).

    Returns:
        set[int]: the still-valid target ids.
    """
    worker_id = to_id(worker)
    if worker_id is None:
        return set()
    orders = linked_to(worker_id, WORK_ORDER_LINK)
    if not orders:
        return set()

    worker_obj = to_object(worker_id)
    host_id = getattr(worker_obj, "host_id", None) if worker_obj is not None else None
    dead_worker = (worker_obj is None
                   or not grid_object_valid(worker_id)
                   or host_id is None
                   or has_role(host_id, "exploded"))
    if dead_worker:
        if purge:
            unlink(worker_id, WORK_ORDER_LINK, set(orders))
        return set()

    on_ship = grid_objects(host_id)
    live = set()
    stale = set()
    for node_id in orders:
        if (to_object(node_id) is None
                or grid_valid_blob(node_id) is None
                or node_id not in on_ship
                or work_order_is_satisfied(node_id)):
            stale.add(node_id)
        else:
            live.add(node_id)
    if purge and stale:
        unlink(worker_id, WORK_ORDER_LINK, stale)
        for node_id in stale:
            if not work_order_workers(node_id):
                set_inventory_value(node_id, _ORDER_KEY, None)
                remove_role(node_id, MAINTENANCE_ROLE)
    return live


def work_order_purge_worker(worker):
    """Sweep one team's orders. Returns how many were dropped."""
    before = len(linked_to(to_id(worker), WORK_ORDER_LINK))
    return before - len(work_orders_for(worker))


def work_order_purge_ship(id_or_obj):
    """Sweep every team on a ship. Returns how many orders were dropped.

    For the events that invalidate every id at once - a ship destroyed, an interior
    rebuilt - where waiting for each team's next read would leave the console
    reporting orders on nodes that no longer exist.
    """
    ship_id = to_id(id_or_obj)
    if ship_id is None:
        return 0
    dropped = 0
    for worker_id in list(grid_objects(ship_id) & has_link(WORK_ORDER_LINK)):
        dropped += work_order_purge_worker(worker_id)
    return dropped


def work_order_targets(id_or_obj):
    """Every node on this ship that has an order, whoever it is assigned to."""
    ship_id = to_id(id_or_obj)
    if ship_id is None:
        return set()
    targets = set()
    for worker_id in grid_objects(ship_id) & has_link(WORK_ORDER_LINK):
        targets |= work_orders_for(worker_id)
    return targets


def work_order_rows(id_or_obj):
    """Every order on a ship as display rows, highest priority first.

    Args:
        id_or_obj: the ship.

    Returns:
        list[dict]: ``target``, ``name``, ``kind``, ``priority``, ``state`` and a
        sorted ``workers`` list of team names.
    """
    ship_id = to_id(id_or_obj)
    if ship_id is None:
        return []
    rows = []
    for node_id in work_order_targets(ship_id):
        node = to_object(node_id)
        if node is None:
            continue
        workers = [to_object(w) for w in work_order_workers(node_id)]
        rows.append({
            "target": node_id,
            "name": node.name,
            "kind": work_order_kind(node_id) or KIND_REPAIR,
            "priority": work_order_priority(node_id),
            "state": grid_node_state(node_id),
            "workers": sorted(w.name for w in workers if w is not None),
        })
    rows.sort(key=lambda r: (-r["priority"], r["name"]))
    return rows


def work_order_best(worker, committed=None, room=None):
    """Which order this team should be walking to right now.

    Highest live priority band, closest within it - and the team STAYS COMMITTED to
    what it already chose unless something strictly outranks it. That commit is the
    anti-oscillation property: recomputing the straight-line closest every tick makes
    the choice flip as the team walks the corridor between two orders. With every
    order at the default priority this is exactly the old behavior.

    Args:
        worker: the damcon team.
        committed (int, optional): the target already chosen, from the blackboard.
        room (str, optional): restrict to nodes with this role. Falsy means no
            filter - which is what lets a maintenance order be picked at all.

    Returns:
        int | None: the chosen target id.
    """
    orders = work_orders_for(worker)
    if room:
        orders = orders & role(room)
    if not orders:
        return None
    best = max(work_order_priority(t) for t in orders)
    if committed in orders and work_order_priority(committed) >= best:
        return committed
    band = {t for t in orders if work_order_priority(t) == best}
    # to_id: grid_closest answers with a CloseData, and the committed branch above
    # returns a plain id. A caller that got one of each would work until the day it
    # got the other.
    return to_id(grid_closest(worker, band))
