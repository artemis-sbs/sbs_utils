def _default_kind (node_id):
    """The kind an order on this node defaults to.
    
    Falls back to repair rather than None: a bare `link()` from an older mission was
    always a repair order, and a node that has since been fixed still has to read
    back as the order somebody filed."""
def _default_priority (kind):
    """Repairs outrank maintenance by default; both are movable."""
def add_role (set_holder, role):
    """Add a role to one or more agents.
    
    THE SERVER CONSOLE COUNTS. `to_object(0)` returns None by design, so this used to
    be a silent no-op for client id 0 - and LM's main screen adds `console, mainscreen`
    to its own client id. On the server window that role was never added, so every
    audience narrowed with `any_role("mainscreen")` - a hail placed on the main screen,
    a hero card, a lower third - resolved to nobody and drew nothing, with no error.
    `to_agent_list` resolves the server the same way `get_inventory_value` always has.
    
    Args:
        set_holder (Agent | int | set[Agent | int]): Agent(s) to update.
        role (str): The role name to add."""
def get_inventory_value (id_or_object, key: str, default=None):
    """Get an inventory value from an agent by key.
    
    Args:
        id_or_object (Agent | int): The agent ID or object.
        key (str): The inventory key.
        default (any, optional): Value returned when the key is absent.
            Defaults to None.
    
    Returns:
        any: The inventory value, or ``default`` if the key is not set."""
def grid_closest (grid_obj, target_set=None, max_dist=None, filter_func=None) -> sbs_utils.agent.CloseData:
    """Find and target the closest object matching the criteria
    
    Args:
        grid_obj (Agent | int): The agent or id
        target_set (set[Agent], optional): The items to test. Defaults to None.
        max_dist (float, optional): max distance. Defaults to None.
        filter_func (Callable, optional): additional filer function. Defaults to None.
    
    Returns:
        CloseData: The gird close data of the closest object"""
def grid_node_is_system (id_or_obj):
    """Is this node part of a ship SYSTEM - the only kind of node that wears?
    
    Every shipped interior says so in its own roles: a system room's roles begin with
    ``system`` (``system,weapon,beam``, ``system,ENGINE,impulse``, ``system,shield,fwd``)
    and a crew space's begin with ``room`` (``room,cabin,gym``, ``room,cabin,quarters``,
    ``room,bay,cargo``). Measured across `data/grid_data.json`: 38 rolesets, 11 of them
    systems, and not one where `system` appears anywhere but first. LegendaryMissions'
    docking repair and the EPad room list already read the same role.
    
    Wear is a SYSTEM idea - a tuned beam array fires harder, a worn impulse drive pushes
    less - and none of that means anything for a gymnasium. Before this, upkeep aged
    every node on the ship, so the gym went worn on schedule and Engineering offered a
    damage-control team to go and tune it.
    
    Damage is different and is deliberately NOT gated: a fire in the galley is a real
    fire, and a team still goes and puts it out."""
def grid_node_state (id_or_obj):
    """The node's condition as one word.
    
    Damage wins over wear - a broken node is "damaged" whatever its wear says,
    which is why grid_damage_grid_object clears `__worn__`.
    
    Args:
        id_or_obj: The grid node (id or Agent).
    
    Returns:
        str: "damaged", "worn", "tuned" or "nominal"."""
def grid_object_valid (id_or_obj) -> bool:
    """Return whether a grid object still has a valid backing space object.
    
    Returns ``False`` once the host ship is destroyed, even though the grid
    object's ``Agent`` may still resolve. See :func:`grid_valid_blob`.
    
    Args:
        id_or_obj (Agent | int): Agent id or object.
    
    Returns:
        bool: ``True`` if the grid object's blob can be safely accessed."""
def grid_objects (so_id) -> set[int]:
    """Get a set of agent ids of the grid objects on the specified ship
    
    Args:
        so_id (Agent | int): agent id or object
    
    Returns:
        set[int]: a set of agent ids"""
def grid_valid_blob (id_or_obj):
    """Return a grid object's engine blob only if its backing space object is
    still valid, otherwise ``None``.
    
    A destroyed host ship leaves the grid object's ``Agent`` and its cached blob
    wrapper in place, so ``to_blob`` still returns a non-``None`` wrapper -- but
    the engine raises ``ValueError: invalid space object`` on any ``get``/``set``
    of that wrapper. This probes cheaply so callers can guard the dead-object
    case with a plain ``is None`` check, the same as a missing object.
    
    Args:
        id_or_obj (Agent | int): Agent id or object.
    
    Returns:
        data_set | None: The live blob, or ``None`` if the object is gone or its
            host space object has been destroyed."""
def has_link (link_name: str):
    """Return the set of agent IDs that have at least one link under a given name.
    
    Despite the ``has_`` prefix this returns a set, not a bool. Use the result
    to iterate or test membership.
    
    Args:
        link_name (str): The link key name.
    
    Returns:
        set[int]: IDs of all agents that own a link entry with this name."""
def has_link_to (link_source, link_name: str, link_target) -> bool:
    """Return whether a source agent has a specific link to a target.
    
    Args:
        link_source (Agent | int): The agent ID or object hosting the link.
        link_name (str): The link key name.
        link_target (Agent | int): The target agent ID or object to check.
    
    Returns:
        bool: ``True`` if the link from source to target exists."""
def has_role (so, role):
    """Return whether an agent currently holds a given role.
    
    Answers for the SERVER console too. It used to always say False for client id 0,
    which reads exactly like "the role is not there" - so a check on the server was
    indistinguishable from a real negative and passed silently for years.
    
    Args:
        so (Agent | int): Agent ID or object.
        role (str): The role name to test for.
    
    Returns:
        bool: ``True`` if the agent has the role."""
def link (set_holder, link_name: str, set_to):
    """Create a named link from one or more source agents to one or more targets.
    
    Args:
        set_holder (Agent | int | set[Agent | int]): Source agent(s).
        link_name (str): The link key name.
        set_to (Agent | int | set[Agent | int]): Target agent(s) to link to."""
def linked_to (link_source, link_name: str):
    """Return the set of IDs that an agent links to under a given name.
    
    Args:
        link_source (Agent | int): The source agent ID or object.
        link_name (str): The link key name.
    
    Returns:
        set[int]: IDs of all linked targets, or an empty set if none."""
def remove_role (agents, role):
    """Remove a role from one or more agents.
    
    Reaches the server console, for the same reason :func:`add_role` does - and it has
    to be the same set, or a console that could gain a role could never lose it.
    
    Args:
        agents (Agent | int | set[Agent | int]): Agent(s) to update.
        role (str): The role name to remove."""
def role (role: str):
    """Return the set of agent IDs that currently hold a given role.
    
    Args:
        role (str): The role name.
    
    Returns:
        set[int]: IDs of all agents with that role."""
def set_inventory_value (so, key: str, value):
    """Set an inventory value on one or more agents.
    
    If ``so`` is a set or collection, every member receives the value.
    
    Args:
        so (Agent | int | set[Agent | int]): The agent(s) to update.
        key (str): The inventory key.
        value (any): The value to store."""
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
def to_set (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """Normalize any agent-like value or collection into a set of integer IDs.
    
    Args:
        other (Agent | CloseData | int | set | list | None): Value to normalize.
    
    Returns:
        set[int]: A set of integer IDs; ``None`` becomes an empty set."""
def unlink (set_holder, link_name: str, set_to):
    """Remove a named link from one or more source agents to one or more targets.
    
    Args:
        set_holder (Agent | int | set[Agent | int]): Source agent(s).
        link_name (str): The link key name.
        set_to (Agent | int | set[Agent | int]): Target agent(s) to unlink."""
def work_order_add (worker, id_or_obj, kind=None, priority=None):
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
        dict | None: the order on the last target touched."""
def work_order_best (worker, committed=None, room=None):
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
        int | None: the chosen target id."""
def work_order_bump (id_or_obj, step=1):
    """Move an order along PRIORITY_STEPS, clamped at both ends.
    
    Args:
        id_or_obj: a grid node.
        step (int, optional): rungs to move; negative lowers. Defaults to 1.
    
    Returns:
        int | None: the new priority, or None if the node has no order."""
def work_order_cancel (worker, id_or_obj):
    """Take one team off a node. The order survives while anyone is still on it."""
def work_order_cancel_all (id_or_obj):
    """Close a node's order for EVERY team on it.
    
    What repair does. Dropping only the repairer's own link left a second team
    walking to a room that was already fixed - the `role("__damaged__")` filter
    stopped them acting on it, silently, but the link itself never went away."""
def work_order_get (id_or_obj, ensure=False):
    """The order on a node, synthesizing one for a bare ``link()``.
    
    Args:
        id_or_obj: a grid node.
        ensure (bool, optional): persist a synthesized record. Defaults to False,
            which keeps this a pure read.
    
    Returns:
        dict | None: ``{"kind": ..., "priority": ...}``, or None when nothing is
        assigned to this node at all."""
def work_order_is_satisfied (id_or_obj):
    """Whether the work this order asked for has been done.
    
    A repair is satisfied when the node is no longer damaged. Maintenance is
    satisfied when the node is **tuned** - not merely when it stopped being worn.
    Reading it as "no longer `__worn__`" made an order on a nominal node instantly
    complete, so it was purged on the first read and a healthy system could never be
    tuned at all.
    
    A node with no order is trivially satisfied."""
def work_order_kind (id_or_obj):
    """The order's kind, or None when the node has no order."""
def work_order_kind_wanted (id_or_obj):
    """What kind of order this node would ACCEPT, or None if there is nothing to gain.
    
    Note "accept", not "need". A **nominal** node takes a maintenance order too -
    tuning it is how a crew earns the tuned tier at all. Gating this on `__worn__`
    made cyan reachable only by neglecting a system and then fixing it, which is the
    exact opposite of rewarding a well-run ship.
    
    But only a SYSTEM node can be tuned. Tuning is what moves a system's
    effectiveness, and a gymnasium has none to move - offering a damage-control team
    to go and tune one was the tell that the model had been applied a room too wide.
    A crew space still takes a REPAIR: a fire in the galley is a real fire.
    
    An already-tuned system answers None too: there is genuinely nothing left to do.
    
    Args:
        id_or_obj: a grid node.
    
    Returns:
        str | None: KIND_REPAIR for a damaged node, KIND_MAINTAIN for a worn or
        nominal SYSTEM, None for a crew space in one piece or a system already at
        spec."""
def work_order_priority (id_or_obj):
    """The order's priority, or 0 when the node has no order."""
def work_order_purge_ship (id_or_obj):
    """Sweep every team on a ship. Returns how many orders were dropped.
    
    For the events that invalidate every id at once - a ship destroyed, an interior
    rebuilt - where waiting for each team's next read would leave the console
    reporting orders on nodes that no longer exist."""
def work_order_purge_worker (worker):
    """Sweep one team's orders. Returns how many were dropped."""
def work_order_rows (id_or_obj):
    """Every order on a ship as display rows, highest priority first.
    
    Args:
        id_or_obj: the ship.
    
    Returns:
        list[dict]: ``target``, ``name``, ``kind``, ``priority``, ``state`` and a
        sorted ``workers`` list of team names."""
def work_order_set_priority (id_or_obj, priority):
    """Set an order's priority. No-op on a node with no order."""
def work_order_targets (id_or_obj):
    """Every node on this ship that has an order, whoever it is assigned to."""
def work_order_workers (id_or_obj):
    """Every team currently assigned to this node.
    
    Args:
        id_or_obj: a grid node.
    
    Returns:
        set[int]: the damcon ids linked to it."""
def work_orders_for (worker, purge=True):
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
        set[int]: the still-valid target ids."""
