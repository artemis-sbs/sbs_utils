from sbs_utils.helpers import FrameContext
def _turret_key (name):
    ...
def _turret_now ():
    ...
def _turret_weakest (tid, cands, rng, expr):
    """Lowest remaining shields among in-range matches - finish something off rather
    than spreading damage. Falls back to None so the caller keeps the nearest."""
def add_role (set_holder, role):
    """Add a role to one or more agents.
    
    Args:
        set_holder (Agent | int | set[Agent | int]): Agent(s) to update.
        role (str): The role name to add."""
def broad_test_around (id_or_obj, width: float, depth: float, broad_type=65520):
    """Return the set of object IDs inside a rectangle centered on an agent or point.
    
    Args:
        id_or_obj (Agent | int | Vec3): Center agent ID, object, or position.
        width (float): Total width of the search rectangle (X axis).
        depth (float): Total depth of the search rectangle (Z axis).
        broad_type (int, optional): Bitmask filtering which object types to
            include. TERRAIN=0x01, NPC=0x10, PLAYER=0x20, ALL=0xffff,
            NPC_AND_PLAYER=0x30. Defaults to 0xfff0.
    
    Returns:
        set[int]: IDs of objects inside the rectangle."""
def clear_target (chasers: set | int | sbs_utils.agent.Agent | sbs_utils.agent.CloseData | sbs_utils.agent.SpawnData, throttle=0):
    """Clear the movement and weapons target on one or more agents.
    
    Sets the target position to the agent's current position and zeroes the
    weapon target ID, effectively stopping pursuit.
    
    Args:
        chasers (Agent | int | set[Agent | int] | CloseData | SpawnData):
            Agent(s) to update.
        throttle (float, optional): Throttle to apply after clearing. Defaults
            to 0."""
def closest (the_ship, the_set, max_dist=None, filter_func=None) -> sbs_utils.agent.CloseData:
    """Return the closest object to a source from a candidate set.
    
    Args:
        the_ship (Agent | int | Vec3): Reference agent ID, object, or position.
        the_set (Agent | int | set[Agent | int]): Candidate agent(s) to test.
        max_dist (float, optional): Maximum distance to consider. Defaults to
            None (no limit).
        filter_func (Callable, optional): Extra predicate ``f(agent) -> bool``.
            Defaults to None.
    
    Returns:
        CloseData | None: Distance data for the closest match, or ``None`` if
            no candidates qualify."""
def closest_in_front (the_ship, the_set, max_dist=None, cone_deg=45.0, filter_func=None) -> sbs_utils.agent.CloseData:
    """Closest object within a forward CONE of the ship's heading (nose-aim targeting).
    
    There is no engine raycast/pick, so this is :func:`closest` restricted to candidates
    whose bearing from the ship is within ``cone_deg`` of ``forward_vector()`` (a cone is
    more forgiving to aim than a true ray). If the ship has no usable heading the cone
    test is skipped (falls back to plain nearest).
    
    Args:
        the_ship: reference ship (id / Agent).
        the_set: candidate ids.
        max_dist (float, optional): max distance. Defaults to None.
        cone_deg (float): half-angle of the forward cone in degrees. Defaults to 45.
        filter_func (Callable, optional): extra ``f(agent) -> bool`` predicate.
    
    Returns:
        CloseData | None: nearest in-cone candidate, or None."""
def get_inventory_value (id_or_object, key: str, default=None):
    """Get an inventory value from an agent by key.
    
    Args:
        id_or_object (Agent | int): The agent ID or object.
        key (str): The inventory key.
        default (any, optional): Value returned when the key is absent.
            Defaults to None.
    
    Returns:
        any: The inventory value, or ``default`` if the key is not set."""
def has_role (so, role):
    """Return whether an agent currently holds a given role.
    
    Args:
        so (Agent | int): Agent ID or object.
        role (str): The role name to test for.
    
    Returns:
        bool: ``True`` if the agent has the role."""
def object_exists (so_id):
    """Return whether an object currently exists in the simulation.
    
    Args:
        so_id (Agent | int): Agent ID or object.
    
    Returns:
        bool: ``True`` if the engine reports the object present."""
def role (role: str):
    """Return the set of agent IDs that currently hold a given role.
    
    Args:
        role (str): The role name.
    
    Returns:
        set[int]: IDs of all agents with that role."""
def role_matches (so, expr):
    """Return whether an agent satisfies a role EXPRESSION.
    
    The expression combines role names (a ship's side counts as a role) with set-style
    operators, evaluated for the single agent ``so``:
    
    * ``|`` OR       -- ``"__player__ | tsn"``     (a player OR a tsn ship)
    * ``&`` AND      -- ``"__player__ & tsn"``     (a tsn player)
    * ``-`` AND-NOT  -- ``"__player__ - cockpit"`` (a player that is not a fighter)
    * ``!`` NOT      -- ``"!tsn"``                 (anything not tsn); ``-`` is BINARY
    * ``( )`` group  -- ``"(tsn | raider) & !__player__"``
    
    Precedence high->low: ``!``, then ``&``/``-`` (left to right), then ``|`` -- use
    parentheses for other groupings. An empty/None expression matches nothing.
    
    Args:
        so (Agent | int): Agent ID or object to test.
        expr (str): The role expression.
    
    Returns:
        bool: ``True`` if the agent satisfies the expression."""
def set_inventory_value (so, key: str, value):
    """Set an inventory value on one or more agents.
    
    If ``so`` is a set or collection, every member receives the value.
    
    Args:
        so (Agent | int | set[Agent | int]): The agent(s) to update.
        key (str): The inventory key.
        value (any): The value to store."""
def side_hostile_ships (observer):
    """Space objects HOSTILE to ``observer`` that are still in the fight.
    
    The diplomacy-only answer to "who may I fight" — the replacement for scoping a
    hostile set by a faction tag such as ``role("raider")``. Allegiance comes from the
    side relations alone, so a ceasefired or defected side drops out the moment its
    diplomacy changes, with no tag to keep in sync; wrecks and surrendered ships are
    excluded because they are not combatants, not because of who they belong to.
    
    Includes hostile stations (they are on a hostile side like anything else). Intersect
    with a CLASS role when you want a narrower kind, e.g.
    ``side_hostile_ships(x) & role("station")`` or ``- role("station")``.
    
    Args:
        observer (str | int | Agent): Side key, side agent ID, or any object whose side
            is the point of view.
    
    Returns:
        set[int]: IDs of hostile, in-the-fight space objects."""
def target_shoot (chasers: set | int | sbs_utils.agent.CloseData | sbs_utils.agent.SpawnData, target_id=None):
    """Set the weapons target on one or more agents without changing their movement.
    
    Args:
        chasers (Agent | int | set[Agent | int] | CloseData | SpawnData):
            Agent(s) to update.
        target_id (Agent | int, optional): The agent to fire at. Defaults to
            None."""
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
def turret_acquire (id_or_obj):
    """Decide what this turret should be shooting, in priority order.
    
    1. A DESIGNATED target, while it lives and is in range. Never re-evaluated.
    2. The CURRENT target, until ``hold_seconds`` expires, while it is inside
       ``range * hold_slack``. A marginally closer candidate does not steal it - this is
       the entire anti-thrash rule, and without it a turret between two enemies flips
       every scan and effectively never fires.
    3. Otherwise, scan: nearest (or weakest) hostile inside range that matches the
       ``targets`` role expression.
    
    Returns:
        int | None: The id to engage, or None if there is nothing to shoot."""
def turret_all ():
    """Every live turret, as a set of ids."""
def turret_candidates (id_or_obj):
    """Everything this turret is willing to shoot, before distance and arc.
    
    Diplomacy decides allegiance via :func:`side_hostile_ships`, which already drops
    wrecks, surrendered ships, and any side that has ceasefired - so a turret stops
    firing the moment a truce is signed, with no tag to keep in sync. Turrets are then
    removed from their own candidate set: an emplacement duelling another emplacement
    while the ships it was built to stop fly past is never what an author wanted."""
def turret_config (id_or_obj, key, default=None):
    """Read one configured value (``range``, ``arc``, ``targets``, ...)."""
def turret_designate (id_or_obj, target_id):
    """Order a turret to shoot a specific thing (a player or GM command).
    
    A designated target beats acquisition entirely and is never re-evaluated against
    closer candidates - the point of an order is that it is not second-guessed. It is
    still dropped when the target dies or leaves ``range * hold_slack``. Pass None to
    return the turret to free-fire."""
def turret_disengage (id_or_obj):
    """Stop shooting and forget the current target."""
def turret_engage (id_or_obj, target_id=None):
    """Point the weapons at a target and NOTHING else.
    
    This is the whole firing mechanism: the engine's beams fire on their own at whatever
    ``target_id`` holds. Deliberately does not touch ``throttle`` or ``target_pos_*`` -
    that is the difference between :func:`target_shoot` and :func:`target`, and it is
    what keeps a turret from wandering off after its victim.
    
    Returns:
        int | None: The engaged target id, or None."""
def turret_in_range (id_or_obj, target_id, slack=True):
    """Whether a target is close enough to keep or take, honoring the hysteresis."""
def turret_is (id_or_obj):
    """Whether an object is a turret."""
def turret_make (id_or_obj, range=None, arc=None, targets=None, priority='closest', hold_seconds=None, hold_slack=None):
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
        int | None: The turret's id, or None if the object does not exist."""
def turret_range (id_or_obj):
    """The turret's configured acquisition range.
    
    Reads what the author set, NOT the hull's beams: the engine keeps beam stats in its
    ship table, so ``beamRange`` on the object reads None (it exists only in the mock and
    on add-on hulls, where sbs_utils wrote it). A turret whose configured range disagrees
    with its hull will acquire targets it cannot hit - keep them in step in shipData."""
def turret_set (id_or_obj, key, value):
    """Change one configured value on a live turret."""
def turret_target (id_or_obj):
    """The turret's current target id, or None."""
def turret_tick (id_or_obj):
    """Acquire and engage in one call - the whole turret loop.
    
    The brain label is a thin wrapper over this so the policy lives in exactly one place
    and Python callers do not have to reimplement it.
    
    Returns:
        int | None: The engaged target, or None if it stood down."""
