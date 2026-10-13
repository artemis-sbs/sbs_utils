def _label_type (label):
    ...
def _orders_hull_armed (obj):
    """Does the hull carry beams or torpedo tubes, per ship data?"""
def _orders_instance_text (display, instance_text):
    ...
def _orders_is_mobile (obj):
    ...
def _orders_labels (prefix, labels=None):
    ...
def _orders_resolve (fn_or_name):
    """An `instances:` provider: a callable, or the name of a MAST global function."""
def _orders_same_or_allied (a, b):
    ...
def _orders_target_fits (valid_for, selected, target, at_point=False):
    """Does `valid_for` (a name or a comma list) accept this target?
    
    self     no target, or the selected object itself
    point    a spot in space with no object (`at_point`)
    allies   own side or allied with the SELECTED object
    hostile  anything else that is a ship
    marker   a marker object
    any      any target (a point, an object, a marker - but not self)"""
def _split (value):
    """`"move, weapons"` / `["move"]` / None -> a set of stripped lowercase names."""
def get_inventory_value (id_or_object, key: str, default=None):
    """Get an inventory value from an agent by key.
    
    Args:
        id_or_object (Agent | int): The agent ID or object.
        key (str): The inventory key.
        default (any, optional): Value returned when the key is absent.
            Defaults to None.
    
    Returns:
        any: The inventory value, or ``default`` if the key is not set."""
def get_ship_data_for (ship_key):
    """Return the full ship data entry for a given key.
    
    Args:
        ship_key (str): The ship type key.
    
    Returns:
        dict | None: Ship data dict, or ``None`` if not found."""
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
def object_exists (so_id):
    """Return whether an object currently exists in the simulation.
    
    Args:
        so_id (Agent | int): Agent ID or object.
    
    Returns:
        bool: ``True`` if the engine reports the object present."""
def orders_available (origin, selected, target=None, labels=None, at_point=False):
    """The order labels `origin` may give `selected`, aimed at `target`.
    
    `target` None (or `selected` itself) asks for the orders it gives ITSELF - full stop,
    hold fire - unless `at_point` says it is an empty spot in space, which only `point`
    and `any` orders accept. `labels` overrides the story lookup, for tests.
    
    Returns [] when the origin may not command it at all."""
def orders_can_take (origin, selected, labels=None):
    """Does `selected` have ANY order `origin` could give it? What the "Can order" chip,
    the comms enable route and drag all ask. Ignores the target - any target will do."""
def orders_caps (obj):
    """The set of capabilities an object has: derived, then overridden.
    
    Returns an empty set for a missing object."""
def orders_caps_provider (fn):
    """Register `fn(obj_id) -> iterable of capability names`, added to every object's
    derived set. How an addon contributes a capability this library cannot see (what
    craft are docked at a station). Idempotent. Returns `fn` so it works as a decorator."""
def orders_caps_set (obj, add=None, remove=None):
    """Override an object's capabilities. `add`/`remove` are a name, a comma string or a
    list; each call REPLACES the previous override of that kind. Pass "" to clear one.
    
        orders_caps_set(freighter_id, remove="weapons")   # armed, but will not fight
        orders_caps_set(platform_id, add="weapons")       # a hull this library misreads"""
def orders_holding_fire (obj):
    """True while an object is ordered to hold fire."""
def orders_items (origin, selected, target=None, labels=None, at_point=False):
    """The menu entries for `selected` aimed at `target`: `[(label, instance, text)]`.
    
    Most orders are one entry, with instance None. An order whose label names an
    `instances:` provider - a function `fn(selected_id, label) -> [(key, text)]` - is one
    entry PER INSTANCE, so a station with two wings offers "Launch Red wing" and "Launch
    Gold wing" from a single label. The provider also decides which instances apply right
    now; an order with none is left off the menu. The chosen `instance` key travels to
    the objective as `order_instance`."""
def orders_may_command (origin, selected):
    """May `origin` give orders to `selected` AT ALL - before asking what it can do?
    
    Not `no_orders`; then the defender role, or an NPC on the origin's own side or an
    allied one."""
def orders_mounted_turrets (obj):
    """The turret mounts welded to a host - where a STATION's weapon orders go."""
def orders_set_prefix (obj):
    """The label-type prefix an object's orders come from: its `give_orders_type`, or
    every order."""
def orders_stance (obj):
    """"free" (the default) or "hold"."""
def orders_stance_set (obj, stance):
    """Weapons free or hold fire. A host passes it on to its turret mounts, since they
    are what does its shooting. Returns the stance set, or None for a bad value."""
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
